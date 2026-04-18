"""Wire translation edge cases."""

from __future__ import annotations

import pytest

from brain.wire import to_wire, translate


def test_to_wire_backcompat_shim():
    msgs = to_wire({"behavior": "estop", "params": {}})
    assert msgs == [{"c": "estop"}]


def test_to_wire_stop_returns_list():
    msgs = to_wire({"behavior": "stop", "params": {}})
    assert isinstance(msgs, list)
    assert len(msgs) == 2


def test_translate_unknown_behavior_raises():
    with pytest.raises(ValueError, match="no wire translation"):
        translate({"behavior": "fly", "params": {}})


def test_walk_partial_params_stride_only():
    out = translate({"behavior": "walk", "params": {"stride": 200}})
    assert out.messages == [{"c": "walk", "on": True, "stride": 200}]


def test_walk_partial_params_step_only():
    out = translate({"behavior": "walk", "params": {"step_ms": 300}})
    assert out.messages == [{"c": "walk", "on": True, "step": 300}]


def test_wire_warning_str():
    from brain.wire import WireWarning
    w = WireWarning("bow_front", "transition", "bounce", "not supported")
    assert "bow_front" in str(w)
    assert "transition" in str(w)
