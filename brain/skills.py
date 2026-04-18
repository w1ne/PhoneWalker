"""Typed skill library — the agent's tool set.

Each skill is a small, sharply-typed method on :class:`RobotSkills`. The
agent loop in :mod:`brain.agent` exposes them as OpenAI-compatible function
tools and routes calls back to the same instance.

Design notes:

* Skills are the right-sized abstraction for a 4-servo quadruped (see
  ``ROBOTICS_RESEARCH_2026.md`` — VLAs are overkill at this scale;
  LLM + typed skills is the hobbyist-class pattern).
* Every motor skill goes through the existing :class:`Validator` and wire
  translator. The agent cannot emit an unsafe or out-of-vocabulary
  behavior — the validator is the sole gate.
* ``look`` and ``listen`` are stubs by default (no camera/mic wired yet).
  They're in the interface so the agent can learn to call them; plug in
  real perception later without touching the agent.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from brain import validator as V
from brain.memory import Episode, Memory
from brain.schema import vocabulary as vocab
from brain.transport import Brainstem

log = logging.getLogger("brain.skills")


@dataclass
class SkillResult:
    ok: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_tool_string(self) -> str:
        """Condensed representation the agent will see in its tool response."""
        import json as _json

        if self.ok:
            return _json.dumps({"ok": True, **self.data})
        return _json.dumps({"ok": False, "error": self.error})


@dataclass
class RobotSkills:
    brainstem: Brainstem
    memory: Memory
    validator: V.Validator = field(default_factory=V.Validator)

    # --------------------------------------------------------- motor skills

    async def pose(self, name: str, speed: int | None = None) -> SkillResult:
        """Move to a named pose. Names must match the firmware vocabulary."""
        if name not in vocab.POSES:
            return SkillResult(False, error=f"unknown pose {name!r}; known: {sorted(vocab.POSES)}")
        params: dict[str, Any] = {}
        if speed is not None:
            params["speed"] = speed
        cmd = {"v": vocab.SCHEMA_VERSION, "behavior": name, "params": params}
        return await self._send("pose", cmd)

    async def walk(self, stride: int = 150, step_ms: int = 400) -> SkillResult:
        """Start the gait. stride 50–400, step_ms 100–1000."""
        cmd = {
            "v": vocab.SCHEMA_VERSION,
            "behavior": "walk",
            "params": {"stride": stride, "step_ms": step_ms},
        }
        return await self._send("walk", cmd)

    async def jump(self) -> SkillResult:
        cmd = {"v": vocab.SCHEMA_VERSION, "behavior": "jump", "params": {}}
        return await self._send("jump", cmd)

    async def stop(self) -> SkillResult:
        """Stop the gait and return to neutral."""
        cmd = {"v": vocab.SCHEMA_VERSION, "behavior": "stop", "params": {}}
        return await self._send("stop", cmd)

    async def estop(self) -> SkillResult:
        """Emergency stop — cut torque. Use when something is wrong."""
        cmd = {"v": vocab.SCHEMA_VERSION, "behavior": "estop", "params": {}}
        return await self._send("estop", cmd)

    async def wait_ms(self, ms: int) -> SkillResult:
        """Sleep for a bounded interval. Capped at 5000ms to prevent runaway waits."""
        ms = max(0, min(5000, int(ms)))
        await asyncio.sleep(ms / 1000)
        return SkillResult(True, data={"waited_ms": ms})

    # ---------------------------------------------------------- perception

    async def look(self, query: str | None = None) -> SkillResult:
        """Describe what the camera sees. Stub until the phone PWA lands."""
        return SkillResult(
            True,
            data={
                "description": "camera not connected",
                "note": "implement in the phone client; this stub keeps the "
                        "agent interface stable so tool prompting already teaches it to use 'look'",
            },
        )

    async def listen(self, seconds: float = 3.0) -> SkillResult:
        """Return the latest speech transcript. Stub until ASR wired."""
        return SkillResult(
            True,
            data={"transcript": "", "note": "mic not connected; wire Moonshine ASR"},
        )

    # ----------------------------------------------------------- telemetry

    async def status(self) -> SkillResult:
        """Read robot telemetry (positions, voltage, temperature, safety state)."""
        try:
            responses = await self.brainstem.send_raw({"c": "status"})
        except NotImplementedError:
            return SkillResult(False, error=f"{type(self.brainstem).__name__} does not support status")
        except Exception as e:
            return SkillResult(False, error=f"status request failed: {e}")
        for r in responses:
            if r.get("t") == "status":
                return SkillResult(True, data=r)
        return SkillResult(False, error=f"no status response; got {responses}")

    # ------------------------------------------------------------ memory

    def remember(self, key: str, value: Any) -> SkillResult:
        """Store a fact across sessions. value can be any JSON-serialisable thing."""
        try:
            self.memory.remember(key, value)
            return SkillResult(True, data={"key": key})
        except Exception as e:
            return SkillResult(False, error=str(e))

    def recall(self, key: str) -> SkillResult:
        val = self.memory.recall(key)
        if val is None:
            return SkillResult(True, data={"key": key, "value": None, "note": "no fact"})
        return SkillResult(True, data={"key": key, "value": val})

    def list_memories(self) -> SkillResult:
        return SkillResult(True, data={"facts": self.memory.all_facts()})

    def log_episode(self, summary: str, tags: list[str] | None = None) -> SkillResult:
        eid = self.memory.log_episode(summary, tags or [])
        return SkillResult(True, data={"id": eid})

    def recent_episodes(self, n: int = 5) -> SkillResult:
        eps = [_episode_to_dict(e) for e in self.memory.recent_episodes(n)]
        return SkillResult(True, data={"episodes": eps})

    # ----------------------------------------------------------- internals

    async def _send(self, label: str, cmd: dict[str, Any]) -> SkillResult:
        try:
            validated = self.validator.validate(cmd)
        except V.ValidationError as e:
            return SkillResult(False, error=f"validator rejected {label}: {e}")
        try:
            responses = await self.brainstem.send(validated)
        except Exception as e:
            return SkillResult(False, error=f"brainstem error: {e}")
        errors = [r for r in responses if r.get("t") == "err"]
        if errors:
            return SkillResult(False, error=f"firmware error: {errors}")
        return SkillResult(True, data={"responses": responses, "seq": validated.get("seq")})


def _episode_to_dict(e: Episode) -> dict[str, Any]:
    return {"id": e.id, "ts_ms": e.ts_ms, "summary": e.summary, "tags": e.tags}
