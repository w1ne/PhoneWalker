"""Validator: the one mandatory layer between an LLM and the brainstem.

Replaces the earlier gap-based rate limiter with a "behavior in progress"
tracker. A non-emergency command that arrives while the previous behavior
is still running is rejected; emergency stops always preempt. This matches
how a real robot behaves (one motion at a time) rather than being a
timer-theater safeguard.

Also more tolerant of real-LLM output: strips markdown code fences, extracts
the first balanced JSON object from surrounding prose, accepts unknown
top-level fields (logged & ignored).
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from brain.schema import vocabulary as v

log = logging.getLogger("brain.validator")


class ValidationError(ValueError):
    pass


@dataclass
class Validator:
    allowed_behaviors: frozenset[str] = field(
        default_factory=lambda: frozenset(v.BEHAVIORS)
    )
    clock: Any = field(default=lambda: int(time.monotonic() * 1000))
    _last_seq: int = 0
    # Epoch-ms at which the current behavior is expected to finish. Commands
    # that arrive before this are rejected unless emergency.
    _busy_until_ms: int = 0

    def validate(self, raw: str | dict[str, Any]) -> dict[str, Any]:
        obj = self._coerce(raw)
        self._check_schema(obj)
        self._whitelist(obj)
        self._clamp_params(obj)
        self._check_busy(obj)
        return self._stamp(obj)

    # ---------------------------------------------------------------- parsing

    def _coerce(self, raw: str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(raw, dict):
            return dict(raw)
        if not isinstance(raw, str):
            raise ValidationError(f"bad input type: {type(raw).__name__}")
        cleaned = _strip_markdown_fence(raw).strip()
        # Tolerate prose around the JSON: grab the first balanced {...}.
        obj_text = _first_json_object(cleaned)
        if obj_text is None:
            raise ValidationError(f"no json object in: {cleaned[:120]!r}")
        try:
            return json.loads(obj_text)
        except json.JSONDecodeError as e:
            raise ValidationError(f"json parse failed: {e}") from e

    def _check_schema(self, obj: dict[str, Any]) -> None:
        if obj.get("v") != v.SCHEMA_VERSION:
            raise ValidationError(f"bad schema version: {obj.get('v')!r}")
        if "behavior" not in obj or not isinstance(obj["behavior"], str):
            raise ValidationError("missing behavior")
        params = obj.setdefault("params", {})
        if not isinstance(params, dict):
            raise ValidationError("params must be object")
        # Strip unknown top-level fields to keep the wire compact; log once.
        extras = set(obj) - {"v", "behavior", "params", "reason", "seq", "ts_ms"}
        for k in extras:
            log.debug("dropping unknown top-level field: %s", k)
            obj.pop(k, None)

    def _whitelist(self, obj: dict[str, Any]) -> None:
        b = obj["behavior"]
        if b not in self.allowed_behaviors:
            raise ValidationError(f"unknown behavior: {b!r}")

    def _clamp_params(self, obj: dict[str, Any]) -> None:
        params = obj["params"]
        for key, (lo, hi, default) in v.PARAM_RANGES.items():
            if key in params:
                try:
                    val = type(default)(params[key])
                except (TypeError, ValueError) as e:
                    raise ValidationError(f"bad {key}: {params[key]!r}") from e
                params[key] = max(lo, min(hi, val))
        if "transition" in params and params["transition"] not in v.TRANSITIONS:
            raise ValidationError(f"bad transition: {params['transition']!r}")
        # Drop unknown params silently — keeps the wire defined.
        allowed_params = set(v.PARAM_RANGES) | {"transition"}
        for k in list(params):
            if k not in allowed_params:
                log.debug("dropping unknown param: %s", k)
                params.pop(k)

    # ------------------------------------------------------- busy/preemption

    def _check_busy(self, obj: dict[str, Any]) -> None:
        if obj["behavior"] == "estop":
            return
        now = self.clock()
        if now < self._busy_until_ms:
            raise ValidationError(
                f"busy: previous behavior finishes in "
                f"{self._busy_until_ms - now}ms"
            )

    def _stamp(self, obj: dict[str, Any]) -> dict[str, Any]:
        self._last_seq += 1
        now = self.clock()
        obj["seq"] = self._last_seq
        obj["ts_ms"] = now

        if obj["behavior"] == "estop":
            # estop preempts and clears the busy window.
            self._busy_until_ms = 0
        elif obj["behavior"] == "walk":
            # walk is continuous — it ends on an explicit stop/estop.
            self._busy_until_ms = 0
        else:
            duration = obj["params"].get(
                "duration_ms", v.DEFAULT_DURATION_MS.get(obj["behavior"], 800)
            )
            hold = obj["params"].get("hold_ms", 0)
            self._busy_until_ms = now + int(duration) + int(hold)
        return obj


# -------------------------------------------------------- emergency pathways


def is_emergency_transcript(text: str) -> bool:
    """Text-layer bypass: phrases that go straight to estop.

    Only fires on short utterances (≤4 words) that contain an emergency
    keyword. "kill" in "I killed it at the dance" won't trigger; "freeze"
    alone will. The ESP32 has its own watchdog — this is convenience, not
    authority.
    """
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) > 4:
        return False
    return bool(set(words) & set(v.EMERGENCY_TRANSCRIPTS))


def emergency_stop_command() -> dict[str, Any]:
    return {
        "v": v.SCHEMA_VERSION,
        "behavior": "estop",
        "params": {},
        "reason": "text-layer bypass",
    }


# ----------------------------------------------------------- text scrubbing


_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _strip_markdown_fence(text: str) -> str:
    m = _FENCE_RE.search(text)
    return m.group(1) if m else text


def _first_json_object(text: str) -> str | None:
    """Return the first balanced {...} in text, honoring string escapes."""
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                return text[start : i + 1]
    return None
