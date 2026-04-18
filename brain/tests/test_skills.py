"""Skills against the real PyBullet sim."""

from __future__ import annotations

import pytest

pytest.importorskip("pybullet")

from brain.memory import Memory
from brain.skills import RobotSkills
from brain.transport import SubprocessBrainstem


@pytest.fixture
async def rig():
    bs = SubprocessBrainstem()
    await bs.start()
    mem = Memory(":memory:")
    skills = RobotSkills(brainstem=bs, memory=mem)
    yield skills
    await bs.stop()
    mem.close()


async def test_pose_bow(rig):
    r = await rig.pose("bow_front")
    assert r.ok, r.error


async def test_pose_rejects_unknown(rig):
    r = await rig.pose("wiggle_hips")
    assert not r.ok
    assert "unknown pose" in r.error


async def test_walk_then_stop(rig):
    assert (await rig.walk(stride=150, step_ms=400)).ok
    assert (await rig.stop()).ok


async def test_jump(rig):
    # jump needs to preempt the busy tracker only via a fresh validator or wait
    await rig.wait_ms(1500)  # let any previous busy window clear
    assert (await rig.jump()).ok


async def test_estop(rig):
    r = await rig.estop()
    assert r.ok


async def test_status(rig):
    r = await rig.status()
    assert r.ok, r.error
    assert "p" in r.data  # positions
    assert len(r.data["p"]) == 4


def test_memory_skills_roundtrip():
    # no brainstem needed for memory-only skills
    import asyncio as _asyncio

    async def _run():
        from brain.transport import StdoutBrainstem
        bs = StdoutBrainstem()
        await bs.start()
        mem = Memory(":memory:")
        skills = RobotSkills(brainstem=bs, memory=mem)

        r = skills.remember("user_name", "Andrii")
        assert r.ok
        r = skills.recall("user_name")
        assert r.ok and r.data["value"] == "Andrii"
        r = skills.log_episode("said hi", ["greeting"])
        assert r.ok
        r = skills.recent_episodes(3)
        assert r.ok and r.data["episodes"][0]["summary"] == "said hi"
        mem.close()

    _asyncio.run(_run())
