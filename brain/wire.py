"""Translate the brain's behavior schema to the firmware wire protocol.

Brain-side schema (LLM-friendly):
    {"v":1,"behavior":"bow_front","params":{"speed":1800},"seq":1,"ts_ms":...}

Firmware wire protocol (firmware/src/CommandProcessor.h):
    {"c":"pose","n":"bow_front","d":1800}
    {"c":"walk","on":true,"stride":150,"step":400}
    {"c":"estop"}

The translator is explicit about what it drops. Every lost field is recorded
as a :class:`WireWarning` so callers can surface it — silent information loss
was a bug in the previous version.

Field mapping notes:

* ``speed`` is the firmware-native ST servo speed (100-3400, default 1500).
  Higher = faster motion. This maps straight to ``d`` on ``pose`` commands.
* ``duration_ms`` is a phone-side timing hint. The firmware has no notion of
  it — motion ends when the servos settle. If both ``speed`` and
  ``duration_ms`` are present we keep ``speed``; if only ``duration_ms`` is
  present we emit a warning and fall back to the default servo speed. Closing
  the gap (converting duration → speed) requires knowing the delta between
  current and target positions, which we don't have here.
* ``transition`` (instant/linear/smooth/bounce) is a phone-side interpolation
  concept. Useful when the brain plays back a choreography; meaningless on a
  single pose command that the firmware executes with its own speed-limited
  trapezoidal profile. Dropped with a warning.
* ``hold_ms`` is consumed by the brain's busy tracker, not the firmware.
  Dropped from the wire silently — it never belonged there.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from brain.schema import vocabulary as v


@dataclass
class WireWarning:
    behavior: str
    field: str
    value: Any
    why: str

    def __str__(self) -> str:
        return f"{self.behavior}.{self.field}={self.value!r}: {self.why}"


@dataclass
class WireOutput:
    """Result of wire translation. ``messages`` is always a list (len ≥ 1)."""

    messages: list[dict[str, Any]]
    warnings: list[WireWarning] = field(default_factory=list)


def translate(command: dict[str, Any]) -> WireOutput:
    behavior = command["behavior"]
    params = command.get("params", {})
    warnings: list[WireWarning] = []

    if behavior in v.POSES:
        msg: dict[str, Any] = {"c": "pose", "n": behavior}
        if "speed" in params:
            msg["d"] = params["speed"]
        elif "duration_ms" in params:
            warnings.append(WireWarning(
                behavior, "duration_ms", params["duration_ms"],
                "firmware has no duration; use 'speed' instead — falling back to default",
            ))
        if "transition" in params:
            warnings.append(WireWarning(
                behavior, "transition", params["transition"],
                "firmware uses built-in trapezoidal profile; transition is informational",
            ))
        return WireOutput([msg], warnings)

    if behavior == "walk":
        msg = {"c": "walk", "on": True}
        if "stride" in params:
            msg["stride"] = params["stride"]
        if "step_ms" in params:
            msg["step"] = params["step_ms"]
        return WireOutput([msg], warnings)

    if behavior == "jump":
        if params:
            warnings.extend(
                WireWarning(behavior, k, vv, "jump takes no params; ignored")
                for k, vv in params.items()
            )
        return WireOutput([{"c": "jump"}], warnings)

    if behavior == "stop":
        return WireOutput(
            [{"c": "walk", "on": False}, {"c": "pose", "n": "neutral"}],
            warnings,
        )

    if behavior == "estop":
        return WireOutput([{"c": "estop"}], warnings)

    raise ValueError(f"no wire translation for behavior: {behavior!r}")


def to_wire(command: dict[str, Any]) -> list[dict[str, Any]]:
    """Back-compat shim: returns the messages, discards warnings.

    New code should call :func:`translate` and inspect the warnings.
    """
    return translate(command).messages
