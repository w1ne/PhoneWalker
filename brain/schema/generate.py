"""Generate behavior.schema.json and behavior.gbnf from vocabulary.py."""

from __future__ import annotations

import json
from pathlib import Path

from brain.schema import vocabulary as v

HERE = Path(__file__).parent


def build_json_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PhoneWalker Behavior Command",
        "type": "object",
        "required": ["v", "behavior"],
        # Unknown top-level fields are allowed — real LLMs produce extras.
        # The validator logs and strips them rather than failing.
        "additionalProperties": True,
        "properties": {
            "v": {"const": v.SCHEMA_VERSION},
            "behavior": {"enum": list(v.BEHAVIORS)},
            "params": {
                "type": "object",
                "additionalProperties": True,
                "properties": {
                    "speed": _int_range("speed"),
                    "duration_ms": _int_range("duration_ms"),
                    "hold_ms": _int_range("hold_ms"),
                    "stride": _int_range("stride"),
                    "step_ms": _int_range("step_ms"),
                    "transition": {"enum": list(v.TRANSITIONS)},
                },
            },
            "reason": {"type": "string", "maxLength": 120},
            "seq": {"type": "integer", "minimum": 0},
            "ts_ms": {"type": "integer", "minimum": 0},
        },
    }


def _int_range(key: str) -> dict:
    lo, hi, _ = v.PARAM_RANGES[key]
    return {"type": "integer", "minimum": lo, "maximum": hi}


def build_gbnf() -> str:
    """GBNF grammar for llama.cpp-style constrained decoding.

    Each rule lives on a single line — llama.cpp's GBNF parser is picky
    about multi-line continuations. Constrains v, behavior, and params.
    reason is optional free text. seq and ts_ms are stamped by the validator
    post-decode.
    """
    behaviors = " | ".join(f'"\\"{b}\\""' for b in v.BEHAVIORS)
    transitions = " | ".join(f'"\\"{t}\\""' for t in v.TRANSITIONS)
    lines = [
        'root ::= "{" ws "\\"v\\":" ws "1" ws "," ws "\\"behavior\\":" ws behavior ws "," ws "\\"params\\":" ws params ws ("," ws "\\"reason\\":" ws string ws)? "}"',
        f"behavior ::= {behaviors}",
        f"transition ::= {transitions}",
        'params ::= "{" ws (param (ws "," ws param)*)? ws "}"',
        (
            'param ::= "\\"speed\\":" ws integer'
            ' | "\\"duration_ms\\":" ws integer'
            ' | "\\"hold_ms\\":" ws integer'
            ' | "\\"stride\\":" ws integer'
            ' | "\\"step_ms\\":" ws integer'
            ' | "\\"transition\\":" ws transition'
        ),
        'string ::= "\\"" ([^"\\\\] | "\\\\" ["\\\\/bfnrt])* "\\""',
        'integer ::= "-"? ("0" | [1-9] [0-9]*)',
        "ws ::= [ \\t\\n]*",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    (HERE / "behavior.schema.json").write_text(
        json.dumps(build_json_schema(), indent=2) + "\n"
    )
    (HERE / "behavior.gbnf").write_text(build_gbnf())
    print("Wrote behavior.schema.json and behavior.gbnf")


if __name__ == "__main__":
    main()
