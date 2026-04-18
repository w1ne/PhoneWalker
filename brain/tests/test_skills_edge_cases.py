"""Skills edge cases — stubs, clamping, error paths."""

from __future__ import annotations

import asyncio

import pytest

from brain.memory import Memory
from brain.skills import RobotSkills
from brain.transport import StdoutBrainstem


@pytest.fixture
def skills():
    bs = StdoutBrainstem()
    mem = Memory(":memory:")
    s = RobotSkills(brainstem=bs, memory=mem)
    yield s
    mem.close()


async def test_wait_ms_clamps_above_5000(skills):
    r = await skills.wait_ms(99999)
    assert r.ok
    assert r.data["waited_ms"] == 5000


async def test_wait_ms_clamps_negative(skills):
    r = await skills.wait_ms(-100)
    assert r.ok
    assert r.data["waited_ms"] == 0


async def test_look_stub_returns_ok(skills):
    r = await skills.look("is there a person?")
    assert r.ok
    assert "description" in r.data


async def test_listen_stub_returns_ok(skills):
    r = await skills.listen(3.0)
    assert r.ok
    assert "transcript" in r.data


def test_list_memories(skills):
    skills.remember("a", 1)
    skills.remember("b", 2)
    r = skills.list_memories()
    assert r.ok
    assert r.data["facts"] == {"a": 1, "b": 2}


async def test_status_on_unsupported_transport(skills):
    r = await skills.status()
    assert not r.ok
    assert "does not support status" in r.error


def test_skill_result_to_tool_string_ok():
    from brain.skills import SkillResult
    import json
    r = SkillResult(True, data={"x": 1})
    parsed = json.loads(r.to_tool_string())
    assert parsed["ok"] is True
    assert parsed["x"] == 1


def test_skill_result_to_tool_string_error():
    from brain.skills import SkillResult
    import json
    r = SkillResult(False, error="boom")
    parsed = json.loads(r.to_tool_string())
    assert parsed["ok"] is False
    assert parsed["error"] == "boom"
