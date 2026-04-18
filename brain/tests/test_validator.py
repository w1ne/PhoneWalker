"""Unit tests for the validator — no network, no LLM, no hardware."""

from __future__ import annotations

import json

import pytest

from brain import validator as V


def make_raw(**overrides) -> str:
    base = {"v": 1, "behavior": "neutral", "params": {}}
    base.update(overrides)
    return json.dumps(base)


# ---------------------------------------------------------- happy path


def test_happy_path_parses_and_stamps():
    val = _fresh(now=1000)
    out = val.validate(make_raw(behavior="bow_front", params={"hold_ms": 500}))
    assert out["behavior"] == "bow_front"
    assert out["params"]["hold_ms"] == 500
    assert out["seq"] == 1
    assert out["ts_ms"] == 1000


def test_seq_increments():
    val = _fresh()
    a = val.validate(make_raw())
    _advance(val, 10_000)
    b = val.validate(make_raw())
    assert b["seq"] == a["seq"] + 1


def test_dict_input_accepted():
    val = _fresh()
    out = val.validate({"v": 1, "behavior": "lean_left", "params": {}})
    assert out["behavior"] == "lean_left"


# ---------------------------------------------------------- parsing tolerance


def test_tolerates_markdown_code_fence():
    val = _fresh()
    raw = '```json\n{"v":1,"behavior":"bow_front","params":{}}\n```'
    out = val.validate(raw)
    assert out["behavior"] == "bow_front"


def test_tolerates_prose_wrapper():
    val = _fresh()
    raw = 'Sure, here you go: {"v":1,"behavior":"jump","params":{}} — cheers!'
    out = val.validate(raw)
    assert out["behavior"] == "jump"


def test_tolerates_extra_top_level_fields():
    val = _fresh()
    raw = '{"v":1,"behavior":"neutral","params":{},"confidence":0.92}'
    out = val.validate(raw)
    assert "confidence" not in out
    assert out["behavior"] == "neutral"


def test_tolerates_extra_params_fields():
    val = _fresh()
    raw = '{"v":1,"behavior":"neutral","params":{"mood":"happy"}}'
    out = val.validate(raw)
    assert "mood" not in out["params"]


def test_rejects_truly_broken_json():
    val = _fresh()
    with pytest.raises(V.ValidationError):
        val.validate("this is just prose, no json here")


# ---------------------------------------------------------- schema checks


def test_rejects_bad_schema_version():
    val = _fresh()
    with pytest.raises(V.ValidationError):
        val.validate(make_raw(v=999))


def test_whitelist_rejects_unknown_behavior():
    val = _fresh()
    with pytest.raises(V.ValidationError):
        val.validate(make_raw(behavior="launch_rockets"))


def test_whitelist_rejects_fake_walk_forward():
    # walk_forward was in the old fake vocabulary — now it must not validate.
    val = _fresh()
    with pytest.raises(V.ValidationError):
        val.validate(make_raw(behavior="walk_forward"))


def test_clamps_speed_above_max():
    val = _fresh()
    out = val.validate(make_raw(behavior="bow_front",
                                params={"speed": 99_999}))
    assert out["params"]["speed"] == 3400  # max for the servo


def test_clamps_stride_below_min():
    val = _fresh()
    out = val.validate(make_raw(behavior="walk", params={"stride": 1}))
    assert out["params"]["stride"] == 50


def test_rejects_bad_transition():
    val = _fresh()
    with pytest.raises(V.ValidationError):
        val.validate(make_raw(params={"transition": "backflip"}))


# --------------------------------------------------- busy/preemption tracker


def test_busy_tracker_blocks_overlapping_command():
    val = _fresh(now=1000)
    val.validate(make_raw(behavior="bow_front"))  # default ~900ms
    with pytest.raises(V.ValidationError) as exc:
        val.validate(make_raw(behavior="lean_left"))
    assert "busy" in str(exc.value)


def test_busy_tracker_releases_after_duration():
    val = _fresh(now=1000)
    val.validate(make_raw(behavior="bow_front"))
    _advance(val, 5000)
    out = val.validate(make_raw(behavior="lean_left"))
    assert out["behavior"] == "lean_left"


def test_busy_tracker_respects_explicit_duration_ms():
    val = _fresh(now=1000)
    val.validate(make_raw(behavior="bow_front",
                          params={"duration_ms": 200, "hold_ms": 0}))
    _advance(val, 250)
    out = val.validate(make_raw(behavior="lean_left"))
    assert out["behavior"] == "lean_left"


def test_estop_preempts_busy():
    val = _fresh(now=1000)
    val.validate(make_raw(behavior="bow_front"))
    out = val.validate(V.emergency_stop_command())
    assert out["behavior"] == "estop"


def test_walk_does_not_block_followup():
    # walk is continuous; the next command should not be blocked by it.
    val = _fresh(now=1000)
    val.validate(make_raw(behavior="walk", params={"stride": 150, "step_ms": 400}))
    out = val.validate(make_raw(behavior="stop"))
    assert out["behavior"] == "stop"


# ---------------------------------------------------------- emergency


def test_emergency_transcript_detection():
    assert V.is_emergency_transcript("ESTOP!")
    assert V.is_emergency_transcript("robot freeze now")
    assert V.is_emergency_transcript("emergency")
    # "stop" is a normal command (goes to neutral), not an emergency.
    assert not V.is_emergency_transcript("stop walking")
    assert not V.is_emergency_transcript("walk forward please")


# ----------------------------------------------------------- helpers


class _FakeClock:
    def __init__(self, now_ms: int = 0) -> None:
        self.now = now_ms

    def __call__(self) -> int:
        return self.now


def _fresh(now: int = 0) -> V.Validator:
    clock = _FakeClock(now)
    val = V.Validator(clock=clock)
    val._clock_ref = clock  # type: ignore[attr-defined]
    return val


def _advance(val: V.Validator, delta_ms: int) -> None:
    val._clock_ref.now += delta_ms  # type: ignore[attr-defined]
