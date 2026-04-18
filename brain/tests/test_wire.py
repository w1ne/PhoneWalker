"""Wire translation: brain schema -> firmware {c,n,d,...} format.

Covers:
  * message shape (same as firmware expects),
  * explicit WireWarning surfacing when info is dropped,
  * stop/estop multi-message expansions.
"""

from __future__ import annotations

from brain.wire import translate


def test_pose_translation():
    out = translate({"behavior": "bow_front", "params": {"speed": 1800}})
    assert out.messages == [{"c": "pose", "n": "bow_front", "d": 1800}]
    assert out.warnings == []


def test_pose_without_speed_omits_d():
    out = translate({"behavior": "neutral", "params": {}})
    assert out.messages == [{"c": "pose", "n": "neutral"}]
    assert out.warnings == []


def test_duration_ms_without_speed_warns():
    out = translate({"behavior": "bow_front", "params": {"duration_ms": 1000}})
    assert out.messages == [{"c": "pose", "n": "bow_front"}]  # no d
    assert len(out.warnings) == 1
    assert out.warnings[0].field == "duration_ms"
    assert "firmware has no duration" in out.warnings[0].why


def test_speed_wins_over_duration_ms():
    out = translate({
        "behavior": "bow_front",
        "params": {"speed": 1800, "duration_ms": 1000},
    })
    assert out.messages == [{"c": "pose", "n": "bow_front", "d": 1800}]
    # speed is present, so duration_ms is not treated as a fallback — no warning
    assert out.warnings == []


def test_transition_is_warned():
    out = translate({
        "behavior": "bow_front",
        "params": {"transition": "bounce"},
    })
    assert out.messages == [{"c": "pose", "n": "bow_front"}]
    assert any(w.field == "transition" for w in out.warnings)


def test_walk_translation_with_params():
    out = translate({"behavior": "walk",
                     "params": {"stride": 200, "step_ms": 300}})
    assert out.messages == [{"c": "walk", "on": True, "stride": 200, "step": 300}]


def test_walk_without_params():
    out = translate({"behavior": "walk", "params": {}})
    assert out.messages == [{"c": "walk", "on": True}]


def test_jump_translation():
    out = translate({"behavior": "jump", "params": {}})
    assert out.messages == [{"c": "jump"}]


def test_jump_warns_on_params():
    out = translate({"behavior": "jump", "params": {"speed": 2000}})
    assert out.messages == [{"c": "jump"}]
    assert len(out.warnings) == 1


def test_stop_expands_to_two_messages():
    out = translate({"behavior": "stop", "params": {}})
    assert out.messages == [
        {"c": "walk", "on": False},
        {"c": "pose", "n": "neutral"},
    ]


def test_estop_translation():
    out = translate({"behavior": "estop", "params": {}})
    assert out.messages == [{"c": "estop"}]
