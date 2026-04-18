"""End-to-end: utterance → mock LLM → validator → wire → real PyBullet sim.

This is the honest integration test. Launches the actual simulator as a
subprocess and confirms the full pipeline produces valid firmware commands
that the sim accepts.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pybullet")

from brain import validator as V
from brain.llm.mock import MockLLM
from brain.transport import SubprocessBrainstem


@pytest.fixture
async def sim():
    bs = SubprocessBrainstem()
    await bs.start()
    yield bs
    await bs.stop()


async def test_sim_accepts_pose(sim):
    val = V.Validator()
    llm = MockLLM()
    cmd = val.validate(llm.infer("please bow"))
    [resp] = await sim.send(cmd)
    assert resp["t"] == "ack"
    assert resp["c"] == "pose"
    assert resp["ok"] is True


async def test_sim_servos_actually_move_to_pose(sim):
    """Shallow acks aren't enough — read back positions and confirm motion.

    bow_front = [1500, 2500, 1500, 2500] in POSE_TABLE. RF/RB are mirrored
    by the firmware (2*2048 - pos), so physically the right-side servos end
    at 2596 when the logical target is 1500.
    """
    import asyncio as _asyncio
    cmd = V.Validator().validate(MockLLM().infer("please bow"))
    await sim.send(cmd)
    # Let the sim physics settle — it runs at 240Hz.
    await _asyncio.sleep(0.5)
    status = await _request_status(sim)
    positions = status["p"]
    assert len(positions) == 4
    # Left side should be near 1500 and 2500 — allow a wide tolerance because
    # PyBullet won't hit exact targets in 500ms.
    assert abs(positions[0] - 1500) < 400, f"LF: {positions[0]}"
    assert abs(positions[1] - 2500) < 400, f"LB: {positions[1]}"


async def _request_status(sim) -> dict:
    import json as _json
    assert sim._proc is not None and sim._proc.stdin is not None
    sim._proc.stdin.write((_json.dumps({"c": "status"}) + "\n").encode())
    await sim._proc.stdin.drain()
    for _ in range(50):
        line = await sim._proc.stdout.readline()
        if not line:
            break
        try:
            msg = _json.loads(line)
        except _json.JSONDecodeError:
            continue
        if msg.get("t") == "status":
            return msg
    raise AssertionError("no status response")


async def test_sim_accepts_jump(sim):
    val = V.Validator()
    llm = MockLLM()
    cmd = val.validate(llm.infer("jump now"))
    [resp] = await sim.send(cmd)
    assert resp["t"] == "ack"
    assert resp["c"] == "jump"


async def test_sim_accepts_walk_then_stop(sim):
    val = V.Validator()
    llm = MockLLM()
    walk = val.validate(llm.infer("walk forward"))
    resp_walk = await sim.send(walk)
    assert resp_walk[0]["c"] == "walk"
    assert resp_walk[0].get("state") == "walking"

    stop = val.validate(llm.infer("stop"))
    resp_stop = await sim.send(stop)
    # stop expands into {walk off} + {pose neutral}
    assert [r["c"] for r in resp_stop] == ["walk", "pose"]
    assert resp_stop[0].get("state") == "stopped"


async def test_sim_accepts_estop(sim):
    val = V.Validator()
    cmd = val.validate(V.emergency_stop_command())
    [resp] = await sim.send(cmd)
    assert resp["t"] == "ack"
    assert resp["c"] == "estop"


async def test_sim_rejects_unknown_pose_via_wire_path(sim):
    """The validator should have blocked this earlier, but if it didn't the
    sim itself returns an error — defence in depth."""
    # Bypass the validator by constructing a brain command directly.
    # Use a behavior the sim doesn't know to confirm error path.
    # neutral IS known, so inject a pose name through params manipulation:
    # the simplest way is to send a raw wire command via internal API.
    await sim._proc.stdin.drain()  # type: ignore[union-attr]
    import json as _json
    sim._proc.stdin.write((_json.dumps({"c": "pose", "n": "nonexistent"}) + "\n").encode())  # type: ignore[union-attr]
    await sim._proc.stdin.drain()  # type: ignore[union-attr]
    resp = await sim._read_one_ack()
    assert resp["t"] == "err"
