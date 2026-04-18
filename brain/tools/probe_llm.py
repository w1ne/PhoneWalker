"""Probe a real GGUF model through the GBNF + validator + wire pipeline.

Writes a report showing:
  * the raw JSON the model emitted for each prompt,
  * whether the validator accepted it,
  * the wire-format message(s) the firmware would receive,
  * any warnings (dropped fields, etc).

Run:
    python3 -m brain.tools.probe_llm --model models/qwen2.5-0.5b-instruct-q4_k_m.gguf
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from brain import validator as V
from brain.llm.llama_cpp_backend import LlamaCppLLM
from brain.wire import translate

PROMPTS = [
    "please bow to me",
    "do a little jump",
    "walk forward slowly",
    "stretch out diagonally",
    "stop moving",
    "twist to the left",
    "lean right and hold",
    "sit at neutral",
    "hi there robot",
    "you are too close, freeze!",
    "how do i fix a python import error",  # out-of-domain
    "dance for me",  # no direct match
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--n-threads", type=int, default=None)
    args = p.parse_args()

    print(f"loading {args.model}")
    t0 = time.time()
    llm = LlamaCppLLM(args.model, n_threads=args.n_threads)
    print(f"  loaded in {time.time()-t0:.1f}s\n")

    val = V.Validator()
    passed = 0
    total = 0

    for prompt in PROMPTS:
        total += 1
        print(f"─ prompt: {prompt!r}")
        t0 = time.time()
        raw = llm.infer(prompt).strip()
        dt = time.time() - t0
        print(f"  llm ({dt:.2f}s): {raw}")

        try:
            # Fresh validator so busy tracker doesn't reject later prompts.
            val = V.Validator()
            cmd = val.validate(raw)
        except V.ValidationError as e:
            print(f"  ✗ validator: {e}")
            continue
        print(f"  ✓ behavior={cmd['behavior']} params={cmd['params']}")

        result = translate(cmd)
        for w in result.warnings:
            print(f"    ! wire drop: {w}")
        for m in result.messages:
            print(f"    wire → {json.dumps(m)}")
        passed += 1

    print(f"\n{passed}/{total} prompts produced a validated + wire-ready command")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
