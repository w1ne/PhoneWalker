"""Schema/grammar generation is deterministic and self-consistent."""

from __future__ import annotations

import json
from pathlib import Path

from brain.schema import generate, vocabulary as voc

SCHEMA_DIR = Path(generate.__file__).parent


def test_generated_json_schema_is_up_to_date():
    on_disk = json.loads((SCHEMA_DIR / "behavior.schema.json").read_text())
    fresh = generate.build_json_schema()
    assert on_disk == fresh, "run `python -m brain.schema.generate`"


def test_generated_gbnf_is_up_to_date():
    on_disk = (SCHEMA_DIR / "behavior.gbnf").read_text()
    fresh = generate.build_gbnf()
    assert on_disk == fresh, "run `python -m brain.schema.generate`"


def test_every_behavior_in_grammar():
    gbnf = generate.build_gbnf()
    for b in voc.BEHAVIORS:
        assert f'"\\"{b}\\""' in gbnf
