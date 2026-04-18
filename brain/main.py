"""Brain loop entry points.

Two modes:
  * ``--mode single`` (default, legacy Path A): one utterance → one
    behavior, via mock / llama.cpp / deepinfra backends.
  * ``--mode agent``: OpenAI-compatible tool-calling agent loop. The LLM
    sees a typed skill library (pose, walk, jump, status, look, remember,
    recall, log_episode, …) and plans over multiple tool calls per turn.

Usage:
    export DEEPINFRA_API_KEY=...
    python3 -m brain.main --mode agent \\
        --model Qwen/Qwen3-30B-A3B-Instruct-2507

    python3 -m brain.main                     # single-shot, mock LLM
    python3 -m brain.main --transport tcp --host <laptop-ip>
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from brain import validator as V
from brain.llm.mock import MockLLM
from brain.memory import DEFAULT_DB, Memory
from brain.transport import (
    Brainstem,
    StdoutBrainstem,
    SubprocessBrainstem,
    TcpBrainstem,
)

log = logging.getLogger("brain.main")


async def run_single(args: argparse.Namespace) -> int:
    llm = _build_llm(args)
    val = V.Validator()
    bs = _build_transport(args)
    await bs.start()
    loop = asyncio.get_event_loop()
    try:
        while True:
            line = await loop.run_in_executor(None, _read_line)
            if line is None:
                break
            line = line.strip()
            if not line:
                continue

            if V.is_emergency_transcript(line):
                cmd = val.validate(V.emergency_stop_command())
                resp = await bs.send(cmd)
                print(f"→ ESTOP  brainstem: {resp}")
                continue

            raw = await loop.run_in_executor(None, llm.infer, line)
            try:
                cmd = val.validate(raw)
            except V.ValidationError as e:
                print(f"✗ rejected: {e}  raw={raw[:120]!r}")
                continue
            resp = await bs.send(cmd)
            print(
                f"→ {cmd['behavior']} seq={cmd['seq']} "
                f"reason={cmd.get('reason')!r}  brainstem: {resp}"
            )
    finally:
        await bs.stop()
    return 0


async def run_agent(args: argparse.Namespace) -> int:
    from brain.agent import Agent, AgentConfig
    from brain.skills import RobotSkills

    bs = _build_transport(args)
    await bs.start()
    memory = Memory(args.memory_db)
    skills = RobotSkills(brainstem=bs, memory=memory)
    cfg = AgentConfig(
        model=args.model or "Qwen/Qwen3-30B-A3B-Instruct-2507",
        max_steps=args.max_steps,
    )
    agent = Agent(skills, cfg)

    history: list[dict] = []
    loop = asyncio.get_event_loop()
    print(f"agent ready (model={cfg.model}, memory={args.memory_db})")
    try:
        while True:
            line = await loop.run_in_executor(None, _read_line)
            if line is None:
                break
            line = line.strip()
            if not line:
                continue
            if V.is_emergency_transcript(line):
                r = await skills.estop()
                print(f"→ ESTOP: {r.to_tool_string()}")
                continue

            turn = await agent.run(line, history=history)
            for tc in turn.tool_calls:
                print(f"  tool {tc['name']}({_short(tc['args'])}) → {_short(tc['result'])}")
            print(f"🤖 {turn.final_message}")
            if turn.stopped_reason != "completed":
                print(f"  (stopped: {turn.stopped_reason}, steps={turn.steps_used})")

            # keep the last assistant message in history so the agent has
            # short-term conversational memory. Tool results are reset per
            # turn; episodic memory lives in SQLite via log_episode.
            history.append({"role": "user", "content": line})
            history.append({"role": "assistant", "content": turn.final_message})
            if len(history) > 12:
                history = history[-(len(history) // 2 * 2):]  # keep even count
    finally:
        await bs.stop()
        memory.close()
    return 0


def _short(obj, limit: int = 120) -> str:
    import json as _json
    try:
        text = _json.dumps(obj) if not isinstance(obj, str) else obj
    except Exception:
        text = str(obj)
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _read_line() -> str | None:
    try:
        return input("you> ")
    except EOFError:
        return None


def _build_llm(args: argparse.Namespace):
    if args.llm == "mock":
        return MockLLM(messy=args.messy)
    if args.llm == "llama_cpp":
        from brain.llm.llama_cpp_backend import LlamaCppLLM

        grammar = Path(__file__).parent / "schema" / "behavior.gbnf"
        if not args.model:
            sys.exit("--model required for llama_cpp backend")
        return LlamaCppLLM(args.model, grammar)
    if args.llm == "deepinfra":
        from brain.llm.deepinfra_backend import DEFAULT_MODEL, DeepInfraLLM

        return DeepInfraLLM(
            model=args.model or DEFAULT_MODEL,
            force_json=args.force_json,
        )
    sys.exit(f"unknown llm backend: {args.llm}")


def _build_transport(args: argparse.Namespace) -> Brainstem:
    if args.transport == "sim":
        return SubprocessBrainstem(gui=args.gui)
    if args.transport == "tcp":
        return TcpBrainstem(host=args.host, port=args.port)
    if args.transport == "stdout":
        return StdoutBrainstem()
    sys.exit(f"unknown transport: {args.transport}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["single", "agent"], default="single")
    p.add_argument("--llm", choices=["mock", "llama_cpp", "deepinfra"], default="mock",
                   help="single-shot LLM backend (ignored in --mode agent)")
    p.add_argument("--model", help="gguf path (llama_cpp) / model id (deepinfra, agent)")
    p.add_argument("--force-json", action="store_true")
    p.add_argument("--messy", action="store_true")
    p.add_argument("--transport", choices=["sim", "tcp", "stdout"], default="sim")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--gui", action="store_true")
    p.add_argument("--max-steps", type=int, default=8, help="agent loop cap")
    p.add_argument("--memory-db", default=str(DEFAULT_DB))
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    runner = run_agent if args.mode == "agent" else run_single
    raise SystemExit(asyncio.run(runner(args)))


if __name__ == "__main__":
    main()
