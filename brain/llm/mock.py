"""Rule-based mock LLM that emits realistic-messy output.

Maps free-text input to a behavior JSON. Occasionally wraps the JSON in
markdown fences or prose — real LLMs do this and the validator needs to
cope. Used in CI and for headless demos.
"""

from __future__ import annotations

import json
import random
import re

from brain.schema import vocabulary as v

_RULES: tuple[tuple[re.Pattern[str], dict], ...] = (
    (re.compile(r"\b(bow|greet|hello|hi)\b", re.I),
     {"behavior": "bow_front", "params": {}}),
    (re.compile(r"\b(sit|rest|neutral|center)\b", re.I),
     {"behavior": "neutral", "params": {}}),
    (re.compile(r"\b(lean.*left|left.*lean)\b", re.I),
     {"behavior": "lean_left", "params": {}}),
    (re.compile(r"\b(lean.*right|right.*lean)\b", re.I),
     {"behavior": "lean_right", "params": {}}),
    (re.compile(r"\b(stretch)\b", re.I),
     {"behavior": "stretch_diagonal1", "params": {}}),
    (re.compile(r"\b(twist.*left|twist)\b", re.I),
     {"behavior": "twist_front_left", "params": {}}),
    (re.compile(r"\b(twist.*right)\b", re.I),
     {"behavior": "twist_front_right", "params": {}}),
    (re.compile(r"\b(jump|hop)\b", re.I),
     {"behavior": "jump", "params": {}}),
    (re.compile(r"\b(walk|forward|go|march)\b", re.I),
     {"behavior": "walk", "params": {"stride": 150, "step_ms": 400}}),
    (re.compile(r"\b(stop|halt)\b", re.I),
     {"behavior": "stop", "params": {}}),
)

_FALLBACK = {"behavior": "neutral", "params": {}}


class MockLLM:
    name = "mock"

    def __init__(self, messy: bool = False, seed: int | None = None) -> None:
        self.messy = messy
        self._rnd = random.Random(seed)

    def infer(self, prompt: str) -> str:
        template = _FALLBACK
        for pattern, t in _RULES:
            if pattern.search(prompt):
                template = t
                break
        body = {
            "v": v.SCHEMA_VERSION,
            **template,
            "reason": _snippet(prompt),
        }
        text = json.dumps(body)
        if self.messy:
            text = self._noise(text)
        return text

    def _noise(self, text: str) -> str:
        choice = self._rnd.randint(0, 3)
        if choice == 0:
            return f"```json\n{text}\n```"
        if choice == 1:
            return f"Sure! Here's the command:\n{text}\nHope that helps."
        if choice == 2:
            # Extra top-level field that validator must strip.
            obj = json.loads(text)
            obj["confidence"] = self._rnd.random()
            return json.dumps(obj)
        return text


def _snippet(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())[:80]
