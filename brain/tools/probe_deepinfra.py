"""Probe a DeepInfra-hosted model through validator + wire.

Usage:
    export DEEPINFRA_API_KEY=...
    python3 -m brain.tools.probe_deepinfra
    python3 -m brain.tools.probe_deepinfra --model deepseek-ai/DeepSeek-V3.1 --force-json

Compares different DeepInfra models on the same prompt battery as the
local-LLM probe, so you can eyeball quality/latency/cost tradeoffs.
"""

from __future__ import annotations

import argparse
import json
import time

from brain import validator as V
from brain.llm.deepinfra_backend import DEFAULT_MODEL, DeepInfraLLM
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
    "how do i fix a python import error",
    "dance for me",
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--force-json", action="store_true")
    args = p.parse_args()

    print(f"model: {args.model}  force_json={args.force_json}\n")
    llm = DeepInfraLLM(model=args.model, force_json=args.force_json)
    passed = 0
    latencies = []

    for prompt in PROMPTS:
        print(f"─ prompt: {prompt!r}")
        t0 = time.time()
        try:
            raw = llm.infer(prompt).strip()
        except Exception as e:
            print(f"  ✗ api error: {e}")
            continue
        dt = time.time() - t0
        latencies.append(dt)
        print(f"  llm ({dt:.2f}s): {raw[:160]}")

        try:
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

    if latencies:
        avg = sum(latencies) / len(latencies)
        print(f"\n{passed}/{len(PROMPTS)} prompts validated  avg latency {avg:.2f}s")
    return 0 if passed == len(PROMPTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
