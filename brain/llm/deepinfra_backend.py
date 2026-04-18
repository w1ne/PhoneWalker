"""DeepInfra LLM backend — OpenAI-compatible HTTP API, open-source models.

DeepInfra hosts Qwen, Llama, DeepSeek, Gemma and friends behind one
OpenAI-compatible endpoint. Strong candidates for the robot brain:

  * ``Qwen/Qwen3-30B-A3B-Instruct-2507`` — MoE, ~3B active, fast + smart
  * ``Qwen/Qwen2.5-72B-Instruct`` — big, reliable, slightly slower
  * ``deepseek-ai/DeepSeek-V3.1`` — top-tier reasoning, heavier
  * ``meta-llama/Llama-4-Scout-17B-16E-Instruct`` — multimodal-capable

Set ``DEEPINFRA_API_KEY`` in your environment. Stdlib-only — no SDK install.

Usage::

    from brain.llm.deepinfra_backend import DeepInfraLLM
    llm = DeepInfraLLM()            # defaults to Qwen3-30B-A3B-Instruct-2507
    print(llm.infer("please bow"))

The validator catches malformed output, so prompt-level JSON coaxing is
enough here. For stricter shape, flip ``force_json=True`` to enable
``response_format: {"type": "json_object"}`` — supported by most
DeepInfra models; check the model card first.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger("brain.llm.deepinfra")

DEFAULT_MODEL = "Qwen/Qwen3-30B-A3B-Instruct-2507"
DEFAULT_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

SYSTEM_PROMPT = """You control a small 4-legged robot. Emit exactly one JSON
object describing what the robot should do. No prose, no code fences.

Schema:
  {"v":1,"behavior":"<one of vocab>","params":{...},"reason":"<=80 chars"}

Vocabulary (pick the best match):
  neutral, bow_front, lean_left, lean_right,
  stretch_diagonal1, stretch_diagonal2,
  twist_front_left, twist_front_right,
  walk, jump, stop, estop

Optional params keys:
  speed (100-3400, servo speed; higher = faster),
  stride (50-400, walk stride),
  step_ms (100-1000, per-step time).

Emit valid JSON only."""


@dataclass
class DeepInfraLLM:
    """Minimal OpenAI-compatible HTTP client against DeepInfra."""

    model: str = DEFAULT_MODEL
    api_key: str | None = None
    url: str = DEFAULT_URL
    temperature: float = 0.2
    max_tokens: int = 200
    force_json: bool = False
    timeout_s: float = 30.0
    system_prompt: str = SYSTEM_PROMPT
    extra_headers: dict[str, str] = field(default_factory=dict)
    name: str = "deepinfra"

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("DEEPINFRA_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "DEEPINFRA_API_KEY not set — pass api_key= or export it"
            )

    def infer(self, prompt: str) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.force_json:
            body["response_format"] = {"type": "json_object"}

        req = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                **self.extra_headers,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:400]
            raise RuntimeError(
                f"deepinfra http {e.code}: {detail}"
            ) from e

        try:
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"deepinfra unexpected shape: {payload!r}") from e
