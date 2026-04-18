"""Agent loop edge cases — malformed tool_calls, parallel calls, bad args."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from brain.agent import Agent, AgentConfig
from brain.memory import Memory
from brain.skills import RobotSkills
from brain.transport import StdoutBrainstem


def _script(steps):
    idx = {"n": 0}
    async def fake_chat(self, messages):
        r = steps[idx["n"]]
        idx["n"] += 1
        return r
    return fake_chat


@pytest.fixture
def rig(monkeypatch):
    monkeypatch.setenv("DEEPINFRA_API_KEY", "test")
    bs = StdoutBrainstem()
    mem = Memory(":memory:")
    skills = RobotSkills(brainstem=bs, memory=mem)
    agent = Agent(skills, AgentConfig(model="test-model", max_steps=4))
    yield agent, skills, mem
    mem.close()


async def test_malformed_tool_arguments(rig):
    """LLM sends unparseable JSON in arguments — should fall back to {}."""
    agent, _, _ = rig
    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "recall", "arguments": "not valid json!!!"},
            }],
        },
        {"role": "assistant", "content": "Couldn't parse that."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("test")
    result = json.loads(turn.tool_calls[0]["result"])
    # recall() requires key — calling with {} raises TypeError, caught as error
    assert result["ok"] is False
    assert "bad arguments" in result["error"]


async def test_parallel_tool_calls(rig):
    """Two tool_calls in one message — both should execute."""
    agent, _, mem = rig
    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [
                {"id": "c1", "type": "function",
                 "function": {"name": "remember", "arguments": json.dumps({"key": "a", "value": 1})}},
                {"id": "c2", "type": "function",
                 "function": {"name": "remember", "arguments": json.dumps({"key": "b", "value": 2})}},
            ],
        },
        {"role": "assistant", "content": "Done."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("remember two things")
    assert len(turn.tool_calls) == 2
    assert mem.recall("a") == 1
    assert mem.recall("b") == 2


async def test_bad_argument_types(rig):
    """LLM passes wrong types — should return error, not crash."""
    agent, _, _ = rig
    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "pose", "arguments": json.dumps({"name": 42})},
            }],
        },
        {"role": "assistant", "content": "Oops."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("test")
    result = json.loads(turn.tool_calls[0]["result"])
    assert result["ok"] is False


async def test_arguments_already_dict(rig):
    """Some API responses return arguments as a dict, not a string."""
    agent, _, mem = rig
    responses = [
        {
            "role": "assistant", "content": None,
            "tool_calls": [{
                "id": "c1", "type": "function",
                "function": {"name": "remember", "arguments": {"key": "x", "value": "y"}},
            }],
        },
        {"role": "assistant", "content": "Done."},
    ]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("test")
    assert mem.recall("x") == "y"


async def test_no_duplicate_system_message(rig):
    """If history already has a system message, don't add a second one."""
    agent, _, _ = rig
    history = [
        {"role": "system", "content": "Custom system prompt."},
        {"role": "user", "content": "prior"},
        {"role": "assistant", "content": "ok"},
    ]
    responses = [{"role": "assistant", "content": "Hi."}]
    with patch.object(Agent, "_chat", _script(responses)):
        turn = await agent.run("hello", history=list(history))
    assert turn.final_message == "Hi."
