"""Tool-calling agent loop.

Takes a goal utterance ("greet whoever walks in"), asks the LLM what to
do, executes whatever tools it calls, feeds results back, repeats until
the LLM returns a final message (no more tool calls) or we hit max-steps.

Uses OpenAI-compatible function-calling — works with DeepInfra, vLLM,
llama-cpp-server, OpenAI directly, anywhere that respects the standard.
Stdlib only; no openai SDK needed.

Architecture reference: see ``ROBOTICS_RESEARCH_2026.md`` — for a 4-servo
platform the LLM-plans-then-calls-typed-skills pattern is the right
abstraction. VLAs are overkill at this DoF.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable

from brain.skills import RobotSkills, SkillResult

log = logging.getLogger("brain.agent")

SYSTEM_PROMPT = """You are the brain of a small 4-legged robot. You have a
body (4 hip servos) and access to tools that move it, sense the world,
and remember things across sessions.

Guiding principles:
- Use tools to act. Don't describe actions in prose.
- One tool call at a time unless the API accepts parallel calls.
- Check the result before proceeding. If something fails, either retry
  with different params, try a different approach, or report the failure.
- The robot can only do one motion at a time. Use `wait_ms` or `status`
  between motions if you're stringing together a sequence quickly.
- Use `remember` / `recall` to persist facts across sessions (names,
  preferences, calibration values). Use `log_episode` to note what you
  did so future-you can plan coherently.
- Never call `estop` unless there's a real emergency. For normal stopping
  use `stop`.
- When the user's request is genuinely ambiguous, ask one clarifying
  question in a final message. Don't guess wildly.

Finish your turn with a short text message summarising what you did or
what you need. No more than 2 sentences.
"""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]            # JSON Schema
    invoke: Callable[..., Any]            # may be sync or async


@dataclass
class AgentConfig:
    model: str
    url: str = "https://api.deepinfra.com/v1/openai/chat/completions"
    api_key_env: str = "DEEPINFRA_API_KEY"
    temperature: float = 0.2
    max_tokens: int = 500
    max_steps: int = 8
    system_prompt: str = SYSTEM_PROMPT
    timeout_s: float = 60.0


@dataclass
class AgentTurn:
    """Result of one `Agent.run` call."""

    final_message: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    steps_used: int = 0
    stopped_reason: str = "completed"


class Agent:
    def __init__(self, skills: RobotSkills, config: AgentConfig) -> None:
        self.skills = skills
        self.config = config
        self.api_key = os.environ.get(config.api_key_env)
        if not self.api_key:
            raise RuntimeError(f"{config.api_key_env} not set")
        self.tools = _build_tool_specs(skills)
        self.openai_tools = [_to_openai_tool(t) for t in self.tools]
        self._by_name = {t.name: t for t in self.tools}

    async def run(
        self,
        user_message: str,
        history: list[dict[str, Any]] | None = None,
    ) -> AgentTurn:
        messages: list[dict[str, Any]] = list(history or [])
        if not messages or messages[0].get("role") != "system":
            messages.insert(0, {"role": "system", "content": self.config.system_prompt})
        messages.append({"role": "user", "content": user_message})

        tool_calls_log: list[dict[str, Any]] = []
        for step in range(self.config.max_steps):
            assistant_msg = await self._chat(messages)
            messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls") or []
            if not tool_calls:
                return AgentTurn(
                    final_message=assistant_msg.get("content") or "",
                    tool_calls=tool_calls_log,
                    steps_used=step + 1,
                )

            for call in tool_calls:
                name = call["function"]["name"]
                raw_args = call["function"].get("arguments", "{}") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    args = {}
                log.info("tool %s(%s)", name, args)
                result = await self._invoke(name, args)
                tool_calls_log.append({"name": name, "args": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": result,
                })

        return AgentTurn(
            final_message=messages[-1].get("content") or "",
            tool_calls=tool_calls_log,
            steps_used=self.config.max_steps,
            stopped_reason="max_steps",
        )

    # -------------------------------------------------------------- llm

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        body = {
            "model": self.config.model,
            "messages": messages,
            "tools": self.openai_tools,
            "tool_choice": "auto",
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }
        req = urllib.request.Request(
            self.config.url,
            data=json.dumps(body).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        loop = asyncio.get_running_loop()
        payload = await loop.run_in_executor(
            None, _http_json_with_retry, req, self.config.timeout_s
        )
        return payload["choices"][0]["message"]

    # ---------------------------------------------------------- dispatch

    async def _invoke(self, name: str, args: dict[str, Any]) -> str:
        spec = self._by_name.get(name)
        if spec is None:
            return json.dumps({"ok": False, "error": f"unknown tool: {name}"})
        try:
            result = spec.invoke(**args) if not inspect.iscoroutinefunction(spec.invoke) \
                else await spec.invoke(**args)
        except TypeError as e:
            return json.dumps({"ok": False, "error": f"bad arguments: {e}"})
        except Exception as e:
            return json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"})

        if isinstance(result, SkillResult):
            return result.to_tool_string()
        return json.dumps({"ok": True, "data": result}, default=str)


# ------------------------------------------------------- tool spec builder


def _build_tool_specs(skills: RobotSkills) -> list[ToolSpec]:
    P = _param   # shorthand
    return [
        ToolSpec(
            "pose",
            "Move to a named pose. One motion at a time — check status or wait before calling again.",
            {"type": "object", "required": ["name"], "properties": {
                "name": P("string",
                    "One of: neutral, bow_front, lean_left, lean_right, "
                    "stretch_diagonal1, stretch_diagonal2, twist_front_left, twist_front_right"),
                "speed": P("integer", "Optional servo speed 100-3400; higher=faster"),
            }},
            skills.pose,
        ),
        ToolSpec(
            "walk",
            "Start continuous walking gait. The robot keeps walking until `stop` is called.",
            {"type": "object", "properties": {
                "stride": P("integer", "Step size 50-400 (default 150)"),
                "step_ms": P("integer", "Time per step 100-1000 (default 400)"),
            }},
            skills.walk,
        ),
        ToolSpec(
            "jump",
            "Perform a single jump. Takes about 1.2 seconds.",
            {"type": "object", "properties": {}},
            skills.jump,
        ),
        ToolSpec(
            "stop",
            "Stop walking and return to neutral pose. Safe, non-emergency.",
            {"type": "object", "properties": {}},
            skills.stop,
        ),
        ToolSpec(
            "estop",
            "EMERGENCY STOP — cuts servo torque. Only when something is wrong.",
            {"type": "object", "properties": {}},
            skills.estop,
        ),
        ToolSpec(
            "wait_ms",
            "Sleep for N milliseconds (capped at 5000). Useful between motions.",
            {"type": "object", "required": ["ms"], "properties": {
                "ms": P("integer", "Milliseconds to wait; 0-5000"),
            }},
            skills.wait_ms,
        ),
        ToolSpec(
            "status",
            "Read live robot telemetry: servo positions, voltage, temperature, safety.",
            {"type": "object", "properties": {}},
            skills.status,
        ),
        ToolSpec(
            "look",
            "Describe what the camera sees. Stubbed until the phone client is wired.",
            {"type": "object", "properties": {
                "query": P("string", "Optional focus hint like 'is there a person?'"),
            }},
            skills.look,
        ),
        ToolSpec(
            "listen",
            "Capture microphone audio and return the latest transcript. Stubbed until ASR is wired.",
            {"type": "object", "properties": {
                "seconds": P("number", "How long to listen (default 3)"),
            }},
            skills.listen,
        ),
        ToolSpec(
            "remember",
            "Store a fact across sessions.",
            {"type": "object", "required": ["key", "value"], "properties": {
                "key": P("string", "Short identifier like 'user_name' or 'preferred_dance'"),
                "value": {"description": "Any JSON-serialisable value"},
            }},
            skills.remember,
        ),
        ToolSpec(
            "recall",
            "Read back a previously-remembered fact.",
            {"type": "object", "required": ["key"], "properties": {
                "key": P("string", "The key passed to `remember`"),
            }},
            skills.recall,
        ),
        ToolSpec(
            "list_memories",
            "List every remembered fact. Use sparingly — the result may be long.",
            {"type": "object", "properties": {}},
            skills.list_memories,
        ),
        ToolSpec(
            "log_episode",
            "Append a short note about what you just did. Shows up in future `recent_episodes` calls.",
            {"type": "object", "required": ["summary"], "properties": {
                "summary": P("string", "One sentence, past tense"),
                "tags": {"type": "array", "items": {"type": "string"},
                         "description": "Optional tags like ['demo', 'greeting']"},
            }},
            skills.log_episode,
        ),
        ToolSpec(
            "recent_episodes",
            "Read the N most recent episode notes to catch up on past context.",
            {"type": "object", "properties": {
                "n": P("integer", "How many episodes; default 5"),
            }},
            skills.recent_episodes,
        ),
    ]


def _param(kind: str, description: str) -> dict[str, Any]:
    return {"type": kind, "description": description}


def _to_openai_tool(t: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        },
    }


def _http_json_with_retry(
    req: urllib.request.Request,
    timeout: float,
    max_retries: int = 3,
) -> dict[str, Any]:
    import time as _time

    for attempt in range(max_retries):
        try:
            fresh = urllib.request.Request(
                req.full_url, data=req.data, headers=dict(req.headers), method=req.method
            )
            with urllib.request.urlopen(fresh, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="replace")[:600]
            if e.code in (429, 502, 503, 529) and attempt < max_retries - 1:
                wait = min(2 ** attempt, 8)
                log.warning("http %d, retry %d/%d in %ds", e.code, attempt + 1, max_retries, wait)
                _time.sleep(wait)
                continue
            raise RuntimeError(f"agent http {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 8)
                log.warning("url error: %s, retry %d/%d in %ds", e.reason, attempt + 1, max_retries, wait)
                _time.sleep(wait)
                continue
            raise RuntimeError(f"agent network error: {e.reason}") from e
    raise RuntimeError("unreachable")
