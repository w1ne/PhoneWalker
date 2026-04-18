"""Full pipeline with a real GGUF model.

Gated on the presence of ``models/<name>.gguf`` and ``llama-cpp-python`` +
``pybullet``. Runs a tiny battery of prompts end-to-end:

    prompt → LlamaCppLLM (Qwen 0.5B via GBNF) → Validator → wire → PyBullet sim

If the gate files aren't present the test is skipped, not failed, so CI
without the model still passes.

To enable locally:

    pip install llama-cpp-python pybullet
    mkdir -p models && cd models
    curl -L -o qwen2.5-0.5b-instruct-q4_k_m.gguf \\
        'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true'
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("pybullet")
pytest.importorskip("llama_cpp")

MODEL_PATH = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
)

if not MODEL_PATH.exists():
    pytest.skip(f"model not found at {MODEL_PATH}", allow_module_level=True)

from brain import validator as V  # noqa: E402
from brain.llm.llama_cpp_backend import LlamaCppLLM  # noqa: E402
from brain.transport import SubprocessBrainstem  # noqa: E402


@pytest.fixture(scope="module")
def llm():
    return LlamaCppLLM(MODEL_PATH)


@pytest.fixture
async def sim():
    bs = SubprocessBrainstem()
    await bs.start()
    yield bs
    await bs.stop()


@pytest.mark.parametrize(
    "prompt,expected_behavior",
    [
        ("please bow", "bow_front"),
        ("jump in place", "jump"),
        ("walk forward", "walk"),
        ("stretch out", {"stretch_diagonal1", "stretch_diagonal2"}),
        ("lean to the right", "lean_right"),
    ],
)
async def test_real_llm_drives_sim(llm, sim, prompt, expected_behavior):
    val = V.Validator()
    raw = llm.infer(prompt)
    cmd = val.validate(raw)

    if isinstance(expected_behavior, set):
        assert cmd["behavior"] in expected_behavior, f"raw={raw!r}"
    else:
        assert cmd["behavior"] == expected_behavior, f"raw={raw!r}"

    responses = await sim.send(cmd)
    assert responses, "sim returned no responses"
    for resp in responses:
        assert resp["t"] == "ack", f"sim err: {resp}"
        assert resp["ok"] is True
