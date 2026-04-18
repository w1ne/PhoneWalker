"""Real LLM backend via llama-cpp-python with GBNF-constrained decoding.

This is the experiment that decides whether the constrained-output
architecture survives contact with a small model. The GBNF grammar at
``brain/schema/behavior.gbnf`` forces the decoder to emit a syntactically
valid behavior JSON; the validator still runs on top for whitelisting,
clamping and busy-tracking.

Install:
    pip install llama-cpp-python

Usage:
    from brain.llm.llama_cpp_backend import LlamaCppLLM
    llm = LlamaCppLLM("models/qwen2.5-0.5b-instruct-q4_k_m.gguf")
    print(llm.infer("please bow"))
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger("brain.llm.llama_cpp")

# Short, behavior-list-in-the-prompt system message. Keeps prefill small.
SYSTEM_PROMPT = """You control a small 4-legged robot. Emit exactly one JSON
object describing what the robot should do. The grammar guarantees shape;
you just pick a sensible behavior.

behavior is one of:
  neutral, bow_front, lean_left, lean_right,
  stretch_diagonal1, stretch_diagonal2,
  twist_front_left, twist_front_right,
  walk, jump, stop, estop

params is always an object. Optional keys:
  speed (100-3400), stride (50-400), step_ms (100-1000).

Reply with JSON only. No prose, no code fences."""


class LlamaCppLLM:
    name = "llama_cpp"

    def __init__(
        self,
        model_path: str | Path,
        grammar_path: str | Path | None = None,
        n_ctx: int = 1024,
        n_gpu_layers: int = 0,
        n_threads: int | None = None,
        verbose: bool = False,
    ) -> None:
        from llama_cpp import Llama, LlamaGrammar

        if grammar_path is None:
            grammar_path = Path(__file__).resolve().parents[1] / "schema" / "behavior.gbnf"

        self._llm = Llama(
            model_path=str(model_path),
            n_ctx=n_ctx,
            n_gpu_layers=n_gpu_layers,
            n_threads=n_threads,
            verbose=verbose,
        )
        self._grammar = LlamaGrammar.from_file(str(grammar_path))

    def infer(self, prompt: str) -> str:
        out = self._llm.create_chat_completion(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            grammar=self._grammar,
            max_tokens=200,
            temperature=0.2,
        )
        return out["choices"][0]["message"]["content"]
