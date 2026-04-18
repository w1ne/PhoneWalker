# PhoneWalker Brain: Model & Runtime Update (April 2026)

Two-week refresh on the phone-brain stack. Qwen2.5-0.5B + llama.cpp + GBNF works (12/12 probe, drives the PyBullet sim); below is what's faster or better now. Supersedes the model-picking and speed sections of `PHONE_BRAIN_RESEARCH.md`.

## 1. Fastest instruction-following small models, right now

New since the earlier report:

- **Qwen3.5 Small** (Mar 2, 2026): 0.8B / 2B / 4B / 9B, Apache-2.0, "built for on-device." 0.8B is the natural drop-in over Qwen2.5-0.5B — same family, meaningfully better instruction following.
- **Gemma 4 E2B / E4B** (Apr 2, 2026): Google's next-gen edge line. Keeps the Gemma 3n MatFormer + PLE architecture. Positioned directly against Qwen3.5 for Android.
- **Qwen3-VL 2B / 4B** (Oct 2025): small-VL variants that actually fit on phones.
- **Phi-4-reasoning-vision-15B** (Mar 4, 2026): too big for phones, noted.

Q4_K_M GGUF, rough tok/s on Snapdragon 8 Gen 3 / A17 Pro, llama.cpp with KleidiAI where applicable:

| Model | Size (Q4) | SD8G3 decode | A17 Pro decode | Structured output |
|---|---|---|---|---|
| Qwen2.5-0.5B (current) | ~310 MB | 55–70 tok/s | 60–80 tok/s | solid w/ grammar |
| **Qwen3.5-0.8B** | ~500 MB | 40–55 tok/s | 45–65 tok/s | noticeably stricter system-prompt adherence |
| Qwen3-1.7B | ~1.0 GB | 22–30 tok/s | 25–35 tok/s | great |
| Llama 3.2 1B | ~750 MB | 25–35 tok/s | 30–40 tok/s | OK, weaker at strict schemas than Qwen |
| **Gemma 3 1B / Gemma 4 E2B** | ~550 MB / ~1.5 GB load, ~2B effective | 25–40 tok/s | 30–45 tok/s | Gemma 3 1B: 40+ tok/s on SME2 silicon |
| Phi-4-mini (3.8B) | ~2.3 GB | 10–20 tok/s | 15–25 tok/s | best reasoner at this size |
| SmolLM3-3B | ~1.8 GB | 12–18 tok/s | 15–22 tok/s | fine but Qwen is stricter |
| Ministral-3B | ~1.8 GB | 12–18 tok/s | 15–22 tok/s | good function calling |

For our command-selection task (short prompt in, constrained JSON out) **Qwen 0.5B/0.8B still wins on raw latency**. Qwen2.5-0.5B at ~55 tok/s on SD8G3 ≈ 40 ms per typical 2–3 token command once prefill is cached. **Qwen3.5-0.8B** is the natural upgrade for ~30% more latency.

Sources: [MarkTechPost on Qwen3.5](https://www.marktechpost.com/2026/03/02/alibaba-just-released-qwen-3-5-small-models-a-family-of-0-8b-to-9b-parameters-built-for-on-device-applications/), [Gemma overview](https://ai.google.dev/gemma/docs/core), [localaimaster 2026 guide](https://localaimaster.com/blog/small-language-models-guide-2026), [Artificial Analysis](https://artificialanalysis.ai/models/qwen3-0.6b-instruct).

## 2. Multimodal in the same bracket

True image + audio in one model at phone-size is still rare:

- **Gemma 3n E2B / E4B / Gemma 4 E2B** — native vision + audio + text. MatFormer lets you run E2B as a submodel of E4B. LiteRT-LM ships `.litertlm` bundles to Android/iOS. Reference platform for multimodal-on-phone today.
- **Qwen2.5-Omni-3B** — text + image + audio + video end-to-end. Runs in MNN Chat on Android. Heavier than Gemma 3n.
- **Qwen3-VL 2B/4B** — image + text only, no audio. Strong grounding.
- **Qwen2.5-VL 3B** — image + text, well-supported in llama.cpp.
- **Phi-4-multimodal (5.6B)** — text + image + audio. #1 OpenASR at release. Too big for comfortable phone use.
- **MiniCPM-o 4.5 (9B)** — full-duplex streaming, "Gemini Flash on your phone" for flagship hardware only.
- **SmolVLM2-500M, Moondream 2 (1.8B)** — image-only, tiny. Great for "what's in frame" at 2–5 fps.
- **PaliGemma 2** — image-only, not streaming.

ViT encoders eat 256–1024 tokens/frame — on a 0.5B text model that dominates context. **Gemma 3n/4 use a MobileNet-v5 style encoder at ~256 tokens/image** and are the only models I'd attempt at 1–2 fps on a mid-range phone.

For robot-action reasoning ("given this frame + this sound, what to do") **Gemma 4 E2B is the only sane default** — only one taking image+audio+text simultaneously, first-class Android runtime via LiteRT-LM.

## 3. KleidiAI / ARM acceleration

KleidiAI is ARM's optimized matmul/quant micro-kernels (i8mm, DotProd, SME, SME2). Integration status:

- **llama.cpp**: integrated. Build with `GGML_CPU_KLEIDIAI=ON`. On load it repacks Q4_0/Q8_0 GGUF into SME2/i8mm layouts.
- **XNNPACK / MediaPipe LLM / LiteRT-LM**: KleidiAI is the default backend for int4/int8 matmul on Arm. That's what Gemma `.task` / `.litertlm` bundles use.
- **PyTorch ExecuTorch**: KleidiAI on by default in XNNPACK backend since ExecuTorch 1.0 GA.

Published numbers:

- **Llama 3.2 quantized on Cortex-A v9 (i8mm)**: ~20% faster decode, **350+ tok/s prefill** on Galaxy S24+.
- **Gemma 2 2B on KleidiAI+XNNPACK**: up to 15× vs unoptimized baseline; **Phi-3/Llama-3 time-to-first-token up to +190%** on Cortex-X925.
- **Gemma 4 2B with SME2 via ExecuTorch**: ~5.5× prefill, 1.6× decode.
- **Gemma 3 generates an 800-word summary in <1 s on a single SME2 core**; 6× over non-SME2.

Gotchas: **SME2** — the big gain — is not universal. ARM's **Lumex cores (2025+)** and **Apple M4 / A18+** have it. **Snapdragon 8 Gen 4 / Elite 2** supports SME1+SVE2 but not SME2 — still a win, smaller. Older phones get i8mm/DotProd only. Minimum Android NDK r26+, API 31+ for the optimized XNNPACK paths.

Sources: [Arm KleidiAI+llama.cpp+SME2 learning path](https://learn.arm.com/learning-paths/mobile-graphics-and-gaming/performance_llama_cpp_sme2/), [Arm Kleidi newsroom](https://newsroom.arm.com/blog/arm-kleidi), [PyTorch/Arm ExecuTorch blog](https://pytorch.org/blog/unleashing-ai-mobile/).

## 4. Prefill / KV-cache for streaming short prompts

Our access pattern (static system prompt + short turn) is the textbook prefix-cache case:

- **llama.cpp**: `--system-prompt-file` (or `cache_prompt: true`, default in llama-server) computes system prefix once and shares across slots. Host-memory prompt caching (discussion #20574) holds multiple warm prefixes. Watch `--cache-reuse` regression in issue #15082.
- **MediaPipe LLM / LiteRT-LM**: a session/cache primitive — init with the system prompt once, clone/branch per turn.
- **Apple Foundation Models**: on-device `LanguageModelSession` reuses cache across `respond(...)` inside one session.

**Speculative decoding on phone**: viable but not free. EdgeLLM (IEEE 2024) and arXiv 2510.15312 show up to 3.8× generation speedup using a tiny draft model on CPU + target on NPU. With a 0.5B target there's nothing smaller to draft with — **spec-decode only pays off at 3B+ targets**. Skip for Path A; revisit for Path B/C.

**Gemma 3n/4 PLE**: a **memory** win, not a speed win. Per-Layer Embeddings offload embedding weights from accelerator memory to CPU RAM, so E4B fits on 8 GB phones. Decode speed comes from MatFormer nesting + KleidiAI/SME2 kernels, not PLE.

Sources: [llama.cpp #20574](https://github.com/ggml-org/llama.cpp/discussions/20574), [#13606](https://github.com/ggml-org/llama.cpp/discussions/13606), [InfoQ on Gemma 3n architecture](https://www.infoq.com/news/2025/07/gemma-3n-architecture/), [arxiv 2510.15312](https://arxiv.org/html/2510.15312v3).

## 5. Opinionated picks

**Path A — text-only, fastest command selection:**

- **Android**: keep llama.cpp, swap to **Qwen3.5-0.8B Q4_K_M**, build with `GGML_CPU_KLEIDIAI=ON`. Google-native alternative: **LiteRT-LM with Gemma 3 1B `.litertlm`** — KleidiAI/SME2 automatic, 40+ tok/s decode + huge prefill on SME2 silicon.
- **iOS**: **Qwen3.5-0.8B Q4** via llama.cpp with Metal, or **Apple Foundation Models on-device** (free structured output via `@Generable`, free KV reuse, Apple Intelligence constraints apply).

If the 12/12 probe pass rate is already good enough, **don't upgrade — stay on Qwen2.5-0.5B**. It's the fastest thing that works.

**Path B/C — camera (and mic):**

- **Android**: **Gemma 4 E2B** (or **Gemma 3n E2B**) via LiteRT-LM. Only <4B-effective model ingesting image + audio + text in one shot. ~8–15 tok/s decode on SD8G3 with image input; ~2 fps reasoning realistic.
- **iOS**: same Gemma 3n/4 E2B via LiteRT-LM (works on iOS), or **Qwen2.5-Omni-3B** via MNN for video+speech-out.
- Image-only fallback: **Qwen2.5-VL-3B** or **Moondream 2** — both well-supported in llama.cpp.

## 6. Last ~60 days, what changes the picture

- **Qwen3.5-0.8B/2B/4B/9B (Mar 2, 2026)** — biggest deal for Path A. 0.8B is the direct upgrade.
- **Gemma 4 (Apr 2, 2026)** — E2B/E4B succeed Gemma 3n; same tricks, better benches, same LiteRT-LM pipeline. Target Gemma 4 directly for new Android multimodal work.
- **Phi-4-reasoning-vision-15B (Mar 4, 2026)** — first Phi with multimodal CoT; relevant only for an edge box.
- **ExecuTorch 1.0 GA** — KleidiAI on by default; PyTorch path is now a real alternative to llama.cpp.
- No Phi-5, no Ministral refresh, no SmolLM4.

## TL;DR

1. Qwen2.5-0.5B baseline is still near-optimal for speed. Upgrade to **Qwen3.5-0.8B** if quality matters more than 15 ms.
2. Rebuild llama.cpp with `GGML_CPU_KLEIDIAI=ON`; on SME2 phones (Lumex, A18+/M4) big free win; on SD8G3/G4 ~20% decode + huge prefill.
3. For multimodal, commit to **Gemma 4 E2B via LiteRT-LM** — only model in the bracket with real image + audio + text + first-class Android/iOS runtime.
4. Use llama.cpp `cache_prompt` / MediaPipe sessions to keep the robot's system prompt hot. Skip spec-decode until 3B+ models.
5. PLE is memory, not speed — don't expect faster tok/s from it.
