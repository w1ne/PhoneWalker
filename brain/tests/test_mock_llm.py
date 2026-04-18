"""Prove the mock LLM's output round-trips through the validator, even messy."""

from __future__ import annotations

import pytest

from brain import validator as V
from brain.llm.mock import MockLLM


@pytest.mark.parametrize(
    "prompt,expected_behavior",
    [
        ("please bow", "bow_front"),
        ("walk forward!", "walk"),
        ("jump now", "jump"),
        ("lean right", "lean_right"),
        ("stretch out", "stretch_diagonal1"),
        ("twist a bit", "twist_front_left"),
        ("please sit down", "neutral"),
        ("stop walking", "stop"),
    ],
)
def test_mock_llm_produces_validated_behavior(prompt, expected_behavior):
    llm = MockLLM()
    val = V.Validator()
    out = val.validate(llm.infer(prompt))
    assert out["behavior"] == expected_behavior


def test_mock_llm_messy_output_still_validates():
    """Simulate real-LLM slop (code fences, prose, extra fields)."""
    llm = MockLLM(messy=True, seed=0)
    val = V.Validator()
    # Each call advances the mock LLM's randomness through all four modes.
    behaviors = []
    for prompt in ["bow", "jump", "lean left", "neutral"]:
        out = val.validate(llm.infer(prompt))
        behaviors.append(out["behavior"])
        val._busy_until_ms = 0  # bypass the busy tracker for this test
    assert behaviors == ["bow_front", "jump", "lean_left", "neutral"]


def test_mock_llm_fallback_is_valid():
    llm = MockLLM()
    val = V.Validator()
    out = val.validate(llm.infer("gibberish xyzzy"))
    assert out["behavior"] == "neutral"
