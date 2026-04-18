"""Scripted agent → real skills → real PyBullet sim.

Proves the agent loop, skills, validator, wire translator, and sim all
compose correctly. The LLM is scripted (not mocked in shape) — the
assistant's tool_calls are the only thing we fake; everything else is
the production path.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

pytest.importorskip("pybullet")

from brain.agent import Agent, AgentConfig
from brain.memory import Memory
from brain.skills import RobotSkills
from brain.transport import SubprocessBrainstem


def _script(steps):
    idx = {"n": 0}

    async def fake_chat(self, messages):
        r = steps[idx["n"]]
        idx["n"] += 1
        return r
    return fake_chat


@pytest.fixture
async def rig(monkeypatch):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test")
    bs = SubprocessBrainstem()
    await bs.start()
    mem = Memory(":memory:")
    skills = RobotSkills(brainstem=bs, memory=mem)
    agent = Agent(skills, AgentConfig(model="test-model", max_steps=8))
    yield agent, skills, mem
    await bs.stop()
    mem.close()


async def test_agent_bow_then_remember(rig):
    """Agent bows, logs the episode, then remembers the user's name."""
    agent, _skills, mem = rig

    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "pose", "arguments": json.dumps({"name": "bow_front"})},
            }],
        },
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c2", "type": "function",
                "function": {"name": "remember",
                             "arguments": json.dumps({"key": "last_greeting", "value": "bow"})},
            }],
        },
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c3", "type": "function",
                "function": {"name": "log_episode",
                             "arguments": json.dumps({"summary": "bowed for the user",
                                                      "tags": ["greeting"]})},
            }],
        },
        {"role": "assistant", "content": "Bowed and saved a note."},
    ]

    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("please greet me with a bow and remember it")

    assert turn.final_message.startswith("Bowed")
    assert [tc["name"] for tc in turn.tool_calls] == ["pose", "remember", "log_episode"]
    # All tool results were ok:
    for tc in turn.tool_calls:
        assert json.loads(tc["result"])["ok"] is True
    assert mem.recall("last_greeting") == "bow"
    assert mem.recent_episodes()[0].summary == "bowed for the user"


async def test_agent_walk_stop_status_cycle(rig):
    """Agent walks, reads status, stops — full round-trip through the sim."""
    agent, _skills, _mem = rig

    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "walk", "arguments": json.dumps({"stride": 150, "step_ms": 400})},
            }],
        },
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c2", "type": "function",
                "function": {"name": "status", "arguments": "{}"},
            }],
        },
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c3", "type": "function",
                "function": {"name": "stop", "arguments": "{}"},
            }],
        },
        {"role": "assistant", "content": "Walked, checked status, stopped."},
    ]

    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("walk for a moment, check how you feel, then stop")

    assert [tc["name"] for tc in turn.tool_calls] == ["walk", "status", "stop"]
    status_result = json.loads(turn.tool_calls[1]["result"])
    assert status_result["ok"] is True
    # status() returns firmware telemetry including positions
    assert "p" in status_result and len(status_result["p"]) == 4
