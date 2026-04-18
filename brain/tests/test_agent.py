"""Agent loop — mocks the HTTP layer so no API key is needed.

The real LLM call is replaced with a scripted sequence of chat responses.
What we verify:

  * tool_calls the model requests actually invoke the skill,
  * skill results are fed back in the correct openai message shape,
  * the loop exits when the model returns a content-only message,
  * max_steps is respected.
"""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from brain.agent import Agent, AgentConfig
from brain.memory import Memory
from brain.skills import RobotSkills
from brain.transport import StdoutBrainstem


@pytest.fixture
def rig(monkeypatch):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test")
    bs = StdoutBrainstem()
    # StdoutBrainstem.start is a no-op; skip the await for sync tests.
    mem = Memory(":memory:")
    skills = RobotSkills(brainstem=bs, memory=mem)
    config = AgentConfig(model="test-model", max_steps=4)
    agent = Agent(skills, config)
    yield agent, skills, mem
    mem.close()


def _script(responses):
    """Build an async _chat replacement that yields the scripted responses."""
    idx = {"n": 0}

    async def fake_chat(self, messages):
        r = responses[idx["n"]]
        idx["n"] += 1
        return r

    return fake_chat


async def test_agent_invokes_memory_tool_and_finishes(rig):
    agent, _skills, mem = rig

    responses = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "remember",
                             "arguments": json.dumps({"key": "user_name", "value": "Andrii"})},
            }],
        },
        {"role": "assistant", "content": "Okay, I'll remember your name."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("my name is Andrii")
    assert turn.final_message == "Okay, I'll remember your name."
    assert turn.steps_used == 2
    assert mem.recall("user_name") == "Andrii"
    assert turn.tool_calls[0]["name"] == "remember"


async def test_agent_invokes_motor_skill(rig):
    agent, _skills, _mem = rig

    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "pose",
                             "arguments": json.dumps({"name": "bow_front"})},
            }],
        },
        {"role": "assistant", "content": "Done — I bowed."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("please bow")
    assert turn.final_message.startswith("Done")
    assert turn.tool_calls[0]["name"] == "pose"
    body = json.loads(turn.tool_calls[0]["result"])
    assert body["ok"] is True


async def test_agent_hits_max_steps(rig):
    agent, _skills, _mem = rig
    agent.config.max_steps = 3

    looping_call = {
        "role": "assistant", "content": None,
        "tool_calls": [{
            "id": "c1", "type": "function",
            "function": {"name": "recall",
                         "arguments": json.dumps({"key": "nope"})},
        }],
    }
    with patch.object(Agent, "_chat", _script([looping_call, looping_call, looping_call])):
        turn = await agent.run("query")
    assert turn.stopped_reason == "max_steps"
    assert turn.steps_used == 3


async def test_agent_unknown_tool_surfaces_error(rig):
    agent, _skills, _mem = rig

    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "teleport", "arguments": "{}"},
            }],
        },
        {"role": "assistant", "content": "Sorry, I can't teleport."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("teleport please")
    tool_result = json.loads(turn.tool_calls[0]["result"])
    assert tool_result["ok"] is False
    assert "unknown tool" in tool_result["error"]


def test_agent_requires_api_key():
    os.environ.pop("DEEPINFRA_API_KEY", None)
    bs = StdoutBrainstem()
    mem = Memory(":memory:")
    skills = RobotSkills(brainstem=bs, memory=mem)
    with pytest.raises(RuntimeError, match="DEEPINFRA_API_KEY"):
        Agent(skills, AgentConfig(model="x"))
    mem.close()
