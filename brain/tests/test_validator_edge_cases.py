"""Edge-case tests flagged by the code review agents."""

from __future__ import annotations

import json

import pytest

from brain import validator as V


class _FakeClock:
    def __init__(self, now_ms: int = 0):
        self.now = now_ms
    def __call__(self):
        return self.now


def _fresh(now: int = 0) -> V.Validator:
    clock = _FakeClock(now)
    val = V.Validator(clock=clock)
    val._clock_ref = clock
    return val


def _advance(val: V.Validator, delta_ms: int) -> None:
    val._clock_ref.now += delta_ms


# ---- input type edge cases

def test_rejects_int_input():
    with pytest.raises(V.ValidationError, match="bad input type"):
        _fresh().validate(42)


def test_rejects_none_input():
    with pytest.raises(V.ValidationError, match="bad input type"):
        _fresh().validate(None)


def test_rejects_list_input():
    with pytest.raises(V.ValidationError, match="bad input type"):
        _fresh().validate([1, 2, 3])


# ---- schema validation edge cases

def test_rejects_missing_behavior_key():
    with pytest.raises(V.ValidationError, match="missing behavior"):
        _fresh().validate(json.dumps({"v": 1, "params": {}}))


def test_rejects_behavior_not_a_string():
    with pytest.raises(V.ValidationError):
        _fresh().validate(json.dumps({"v": 1, "behavior": 42, "params": {}}))


def test_rejects_params_not_a_dict():
    with pytest.raises(V.ValidationError, match="params must be object"):
        _fresh().validate(json.dumps({"v": 1, "behavior": "neutral", "params": "none"}))


def test_rejects_params_as_list():
    with pytest.raises(V.ValidationError, match="params must be object"):
        _fresh().validate(json.dumps({"v": 1, "behavior": "neutral", "params": [1, 2]}))


# ---- param clamping edge cases

def test_speed_string_rejected():
    with pytest.raises(V.ValidationError, match="bad speed"):
        _fresh().validate(json.dumps({"v": 1, "behavior": "neutral", "params": {"speed": "fast"}}))


def test_speed_clamped_below_min():
    val = _fresh()
    out = val.validate(json.dumps({"v": 1, "behavior": "neutral", "params": {"speed": 1}}))
    assert out["params"]["speed"] == 100


def test_hold_ms_clamped_above_max():
    val = _fresh()
    out = val.validate(json.dumps({"v": 1, "behavior": "neutral", "params": {"hold_ms": 99999}}))
    assert out["params"]["hold_ms"] == 5000


def test_step_ms_clamped_both_directions():
    val = _fresh()
    out = val.validate(json.dumps({"v": 1, "behavior": "walk", "params": {"step_ms": 1}}))
    assert out["params"]["step_ms"] == 100
    _advance(val, 5000)
    out = val.validate(json.dumps({"v": 1, "behavior": "walk", "params": {"step_ms": 99999}}))
    assert out["params"]["step_ms"] == 1000


# ---- busy tracker edge cases

def test_hold_ms_extends_busy_window():
    val = _fresh(now=1000)
    val.validate(json.dumps({"v": 1, "behavior": "neutral", "params": {"hold_ms": 3000}}))
    _advance(val, 800)
    with pytest.raises(V.ValidationError, match="busy"):
        val.validate(json.dumps({"v": 1, "behavior": "lean_left", "params": {}}))


# ---- JSON extraction edge cases

def test_first_json_object_with_nested_braces_in_string():
    raw = 'Here: {"v":1,"behavior":"neutral","params":{},"reason":"has {braces} inside"}'
    out = _fresh().validate(raw)
    assert out["behavior"] == "neutral"


def test_first_json_object_with_unbalanced_braces_fails():
    with pytest.raises(V.ValidationError, match="no json object"):
        _fresh().validate("{not closed")


# ---- emergency transcript edge cases

def test_emergency_kill_in_long_sentence_does_not_trigger():
    assert not V.is_emergency_transcript("I killed it at the dance competition last night")


def test_emergency_freeze_alone_triggers():
    assert V.is_emergency_transcript("freeze")


def test_emergency_short_phrase_triggers():
    assert V.is_emergency_transcript("oh no freeze now")


def test_emergency_long_phrase_does_not_trigger():
    assert not V.is_emergency_transcript("please halt all operations on the robot immediately")


def test_emergency_stop_command_shape():
    cmd = V.emergency_stop_command()
    assert cmd["v"] == 1
    assert cmd["behavior"] == "estop"
    assert isinstance(cmd["params"], dict)
    assert "reason" in cmd
