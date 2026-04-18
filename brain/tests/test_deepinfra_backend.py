"""DeepInfra backend — gated tests.

The unit test (no network) always runs. The live test runs only when
``DEEPINFRA_API_KEY`` is set in the environment, keeping CI green by
default without skipping silently on purpose.
"""

from __future__ import annotations

import os

import pytest

from brain import validator as V
from brain.llm.deepinfra_backend import DEFAULT_MODEL, DeepInfraLLM


def test_requires_api_key():
    env_key = os.environ.pop("DEEPINFRA_API_KEY", None)
    try:
        with pytest.raises(RuntimeError, match="DEEPINFRA_API_KEY"):
            DeepInfraLLM()
    finally:
        if env_key is not None:
            os.environ["DEEPINFRA_API_KEY"] = env_key


@pytest.mark.skipif(
    "DEEPINFRA_API_KEY" not in os.environ,
    reason="needs DEEPINFRA_API_KEY for live API call",
)
def test_live_infer_produces_validated_command():
    llm = DeepInfraLLM()
    val = V.Validator()
    raw = llm.infer("please bow to the audience")
    cmd = val.validate(raw)
    assert cmd["behavior"] in {"bow_front", "neutral"}, f"raw={raw!r}"


@pytest.mark.skipif(
    "DEEPINFRA_API_KEY" not in os.environ,
    reason="needs DEEPINFRA_API_KEY for live API call",
)
def test_live_infer_jump():
    llm = DeepInfraLLM()
    val = V.Validator()
    raw = llm.infer("do a jump")
    cmd = val.validate(raw)
    assert cmd["behavior"] == "jump", f"raw={raw!r}"
