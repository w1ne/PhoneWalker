# PhoneWalker Brain Design Report: On-Device AI Stack (April 2026)

## Context grounding

PhoneWalker's existing architecture (per `BRAIN_BRAINSTEM_ARCHITECTURE.md`, `CHOREOGRAPHY_GUIDE.md`, `CONCEPT.md`) gives us a clean target for the brain layer:

- **Brainstem (ESP32)** owns reflexes (<10 ms IMU loop), safety enforcement, servo coordination, and a JSON choreography vocabulary keyed on named poses (`neutral`, `bow_front`, `lean_left`, `stretch_diagonal1`, `twist_front_right`, etc.) plus transition modifiers (`smooth`/`linear`/`bounce`/`instant`).
- **Comms** is already specified: WebSocket+JSON for high-level behavior commands at 1–10 Hz, plus an optional 50 Hz binary realtime channel for direct pose/servo packets. There's also a BLE path per `BLE_PHONE_APP_GUIDE.md`.
- **Form factor twist** (from `CONCEPT.md`): rear camera looks forward through a 45° mirror; front camera looks up; mic/speaker face up. So *vision-language is genuinely useful* — the robot literally sees where it walks.

That means the brain's job is narrow and well-defined: **emit a stream of `{behavior, params}` JSON messages** (and occasionally raw pose commands) at a cadence the ESP32 can already consume. Everything below is in service of that.

---

## 1. On-device model landscape (April 2026)

### Vision-language (the interesting category)

| Model | Size | Modalities | Notes / mobile fit |
|---|---|---|---|
| **Gemma 3n E2B / E4B** | ~2B / ~4B effective (uses Per-Layer Embeddings — actual loaded params lower, ~2GB / ~3GB at int4) | text + image + audio | Designed *explicitly* for on-device. Processes images at 256 tokens each, audio at 6.25 tok/s. Google reports up to 60 fps video sampling on Pixel and ~2x prefill speedup vs Gemma 3 4B via KV-cache sharing. E2B is the right starting point for phones. Apache-2-style Gemma license. |
| **Gemma 3 1B / 4B** | 1B / 4B | 1B is text-only; 4B is multimodal (text+image) | 1B reportedly hits ~2,585 tok/s prefill on a mobile GPU. Good if you don't need audio. |
| **SmolVLM2 256M / 500M / 2.2B** | tiny | text + image (+video sampling) | HuggingFace shipped an iPhone demo doing live video understanding at 500M. 256M uses <1 GB GPU memory. Apache-2.0. The lightest realistic VLM. |
| **Moondream 2 (0.5B / 2B)** | 0.5B / 2B | text + image | 0.5B targets mobile/edge with int4/int8. Strong VQA + grounding. Apache-2.0. |
| **Qwen2.5-VL 3B** | 3B | text + image + video | Window-attention vision encoder; Alibaba's tech report explicitly mentions "operate mobile devices and robots." Tongyi Qianwen License (commercial-friendly with limits). |
| **Qwen2.5-Omni 3B** | 3B | text + image + audio + speech-out | End-to-end omnimodal incl. streaming TTS. Heavier; ambitious for phones today. |
| **PaliGemma 2 (3B/10B)** | 3B+ | text + image | Strong vision encoder (SigLIP). 3B feasible on flagships. Gemma license. |
| **Phi-3.5-vision (4.2B)** | 4.2B | text + image | MIT license. Decent quality but heavier than Gemma 3n E2B. |
| **MiniCPM-V 2.6 (8B)** | 8B | text + image + video | Too big for sustained mobile use; useful as a quality reference. |

### Text-only (for the "perception → text → small LLM" pattern)

- **Gemma 3 1B** — fastest realistic text path on phone.
- **Phi-3.5-mini (3.8B)** — strong instruction following, MIT license.
- **Qwen2.5 1.5B / 3B** — solid JSON/tool-calling.
- **Apple Foundation Models (~3B)** — *free, built into iOS 26+*, with first-class **guided generation** (structured output) and **tool calling**, no model download. iOS-only and Apple Intelligence-eligible devices only, but a massive shortcut on iPhone.

### Audio

- **Whisper tiny (39M) / base (74M) / small (244M)** — universal baseline; tiny is real-time on every modern phone but accuracy is mediocre.
- **Moonshine v2 (Tiny / Small / Medium)** — purpose-built for streaming edge ASR. Tiny hits ~50 ms latency (5.8× faster than Whisper Tiny) with comparable or better WER. Permissive license. **Strong default choice.**
- **WhisperKit** (Apple) — billion-scale Whisper variants quantized for Core ML/ANE; iOS-native.
- **Apple SFSpeechRecognizer / Android SpeechRecognizer** — free, on-device on recent OS versions. Use these when you don't need custom vocab.
- **Porcupine** (Picovoice) — wake-word, ~97 % accuracy, well-tested on iOS+Android background mode; commercial license but free tier.
- **openWakeWord** — open source, slightly better accuracy on some sets, no commercial restrictions; less mobile-polished but workable.

### Realistic tokens/sec on flagship phones (2025 numbers)

- Gemma 3n E2B int4 on Snapdragon 8 Gen 3 GPU: ~15–25 tok/s decode, ~150–300 tok/s prefill (per Google's reported numbers and MLC/MediaPipe benchmarks).
- Gemma 3n E4B: ~10–15 tok/s decode on high-end SoCs.
- Gemma 3 1B (text): 30–60 tok/s decode trivially; can be much higher with NPU.
- A17/A18 Pro and Tensor G3/G4 land in the same ballpark; Apple's NPU (ANE) tends to win latency for small models when targeted via Core ML, while Snapdragon's Hexagon NPU wins via QNN/LiteRT-NPU when the runtime supports it.
- Snapdragon 8 Gen 4 with Llama-class 4-bit models has been reported at 15–22 tok/s; Transformer-Lite (a research stack) hit 121 tok/s prefill / 14 tok/s decode for ChatGLM2-6B on 8 Gen 3.

---

## 2. Runtimes

| Runtime | Platforms | Acceleration | Best for | Tradeoffs |
|---|---|---|---|---|
| **MediaPipe LLM Inference API** | Android, iOS, Web | CPU/GPU, increasingly NPU via LiteRT delegate | Fastest path to "Gemma on phone with vision/audio." Now formally supports multimodal (text+image+audio) on Android. | Google notes they are **migrating users to LiteRT-LM**; treat MediaPipe API as the today-thing, LiteRT-LM as the tomorrow-thing. |
| **LiteRT-LM** (the successor) | Android, iOS, Web, desktop, RPi | CPU/GPU/NPU (Qualcomm Hexagon, MediaTek NeuroPilot) | Production target. Backs Chrome, Chromebook Plus, Pixel Watch on-device GenAI. Supports Gemma, Llama, Phi-4, Qwen. | Newer, smaller community. NPU support varies by chip. |
| **MLC-LLM** | Android, iOS (TestFlight), Linux, web (WebGPU) | GPU primarily (TVM-compiled) | Cross-platform, many models, good GPU perf. | Build/packaging is fiddly; iOS distribution is awkward. |
| **llama.cpp** (incl. Android wrappers, `llama.rn`) | Everything | CPU strong; Vulkan/Metal GPU; experimental NPU | Most flexible: GBNF grammars, tool calling, huge model zoo, multimodal via `mtmd`/llava plugins. | Decoding speed on phone tends to be CPU-bound and below MediaPipe/LiteRT-LM with same model. |
| **ExecuTorch** (PyTorch) | Android, iOS | CPU/GPU/NPU via backends (XNNPACK, CoreML, QNN, MPS) | Native PyTorch → mobile, including Llama and SpinQuant quantization. Aligned with Meta's own LLama mobile demos. | Heavier integration story; smaller off-the-shelf model selection than MediaPipe. |
| **Core ML / Apple Foundation Models / MLX** | iOS/macOS only | ANE (NPU), GPU, CPU | Best iOS performance for hand-tuned models; Foundation Models gives you a free 3B with structured output. MLX is Apple's array framework for custom training/inference on Apple silicon. | iOS-only; if you want one app, you still need a parallel Android stack. |
| **ONNX Runtime Mobile / ORT-GenAI** | Android, iOS | CPU/GPU/NNAPI/CoreML | Great if your model already lives in ONNX (Phi-3.5, etc.). | LLM perf trails MediaPipe/MLC for the popular models. |

**Recommendation for PhoneWalker:** standardize on **MediaPipe LLM Inference / LiteRT-LM on Android** and **Apple Foundation Models (with MediaPipe LLM as fallback for non-Apple-Intelligence devices) on iOS**. Both speak the same prompt-and-JSON-output contract, so the brainstem doesn't care which one is talking.

---

## 3. Input pipelines

### 3a. Vision

There are three viable strategies, in increasing ambition:

1. **Classical CV → text → small LLM** (cheapest, fastest)
   - YOLOv8-nano / YOLO-NAS / MediaPipe Object Detector at 15–30 fps on phone GPU.
   - Optionally MediaPipe Pose + Face + Gestures.
   - Convert detections to a compact text scene description ("person at bearing -20°, distance ~1.2m, hand raised; chair at +30°"), feed to **Gemma 3 1B / Apple Foundation / Phi-3.5-mini** at 0.5–2 Hz to choose a behavior.
   - Latency per cycle: 30–80 ms for vision + 200–600 ms for the LLM call.

2. **Small VLM at low frame rate** (good middle ground)
   - Sample one frame every 0.5–2 s, downscale to 256–384 px, feed to **SmolVLM2 500M, Moondream 0.5B, or Gemma 3n E2B** with a fixed system prompt that asks for a JSON behavior selection.
   - Realistic on-device cadence: **1–3 fps** for SmolVLM/Moondream-tier, **0.3–1 fps** for Gemma 3n E2B with image.
   - Image encoding alone is 256 tokens for Gemma 3n; that dominates prefill cost.

3. **Full multimodal Gemma 3n at higher cadence**
   - With KV-cache sharing and the fact that Gemma 3n is engineered for video framing, you can do 2–5 fps on a Pixel 8/9 Pro–class device for short prompts. This is essentially a System-2 reasoner, not a controller.

**Prompting pattern for "what should the robot do right now":** keep the system prompt tiny, the response schema fixed. Example schema-constrained reply:

```json
{"observation":"person waving at me, ~1m","intent":"greet","behavior":"bow_front","params":{"hold_ms":1500}}
```

The `observation` field is *load-bearing* — it forces the model to ground its choice in what it sees, which empirically reduces hallucinated behaviors. Throw it away after logging.

**Note on VLAs:** True Vision-Language-Action models (π0, GR00T N1, SmolVLA) are interesting reference architecture but inappropriate here — they assume continuous joint-space control, not a 4-DoF choreography vocabulary. The **GR00T N1 dual-system pattern** (System-2 VLM at ~10 Hz + System-1 motor at 120 Hz) does map cleanly onto our Brain/Brainstem split, though.

### 3b. Audio

Three layers:

1. **Wake word**: Porcupine if you can stomach the license (most reliable mobile background story); openWakeWord otherwise. Always-on, <1 % CPU.
2. **Streaming ASR**: **Moonshine Tiny** is the right default — 50 ms latency, edge-tuned, permissive license. Whisper tiny is the lazy fallback.
3. **Intent**: route the transcript to the same small LLM as the vision path with a tool-use prompt; *or* skip the LLM entirely for hard-coded commands ("stop," "sit," "follow me") via a regex/keyword matcher in front of the LLM. The latter is much faster for the obvious cases.

For the conversational path (talking back), Apple's `AVSpeechSynthesizer` and Android's TextToSpeech are free, instant, and good enough. Don't ship a TTS model unless you want a specific voice.

### 3c. Video / temporal context

You almost never want to feed a video clip to an on-device model — too expensive. Practical patterns:

- **Sparse keyframes**: 1 frame every 500 ms, last N=3 frames concatenated when you actually call the LLM. Gemma 3n explicitly supports this.
- **Event-triggered sampling**: classical CV (motion / object-appearance / wake-word) decides *when* to spend a VLM call.
- **Rolling text memory**: keep a 200-token "what I've been doing for the last 30 s" log in the prompt; cheaper than visual history and surprisingly effective for behavior coherence.
- **KV-cache reuse**: pin the system prompt + behavior vocabulary as a cached prefix (MediaPipe and llama.cpp both let you persist KV across calls). On a phone this is a 3–10× prefill win for streaming use.

---

## 4. Output → movement

The choreography system already gives you a closed vocabulary, which is *ideal* for constrained decoding. Build the brain's output around a tiny DSL:

```
behavior  := "neutral" | "bow_front" | "lean_left" | "lean_right"
           | "stretch_diagonal1" | "stretch_diagonal2"
           | "twist_front_left" | "twist_front_right"
           | "walk_forward" | "walk_backward" | "turn_left" | "turn_right"
           | "stop" | "sit" | "play_dance:<name>"
transition := "instant" | "linear" | "smooth" | "bounce"
```

Wrapped in:

```json
{
  "behavior": "<one of vocab>",
  "params": {"speed": 0.0-1.0, "duration_ms": 100-5000, "transition": "<...>", "hold_ms": 0-3000},
  "reason": "<=80 chars>"
}
```

**How to enforce it, by runtime:**

- **llama.cpp**: GBNF grammar over the schema. The model literally cannot emit an invalid behavior name — token sampling is masked. This is the gold standard for safety-critical structured output and is already production-grade.
- **MediaPipe LLM / LiteRT-LM**: function-calling APIs are landing; until they're fully there, use prompt-level JSON-mode plus a post-parse-and-reject loop.
- **Apple Foundation Models**: built-in **guided generation** with `@Generable` Swift types — define the struct, get a guaranteed-shape response. This is the killer iOS shortcut.
- **Outlines / lm-format-enforcer** wrappers exist for ONNX/ExecuTorch paths.

**Validation layer on the phone (not optional):**

1. Parse JSON; reject and re-prompt on failure (max 1 retry, then no-op).
2. Whitelist `behavior` against the actual choreography registry pulled from the ESP32 at boot.
3. Clamp numeric params to physically safe ranges.
4. **Rate limit**: drop any command that arrives <X ms after the previous one (X = expected behavior duration + slack).
5. **Emergency-stop hardcode**: certain transcripts ("stop", "down", "freeze") and certain CV events (imminent fall, IMU spike forwarded from ESP32) bypass the LLM entirely and emit `EMERGENCY_STOP` on the binary channel.
6. Log the model's `reason` field with each command for postmortem debugging.

This validation layer is your contract with the brainstem. The ESP32 already does its own bounds checking; the phone-side check is about catching nonsense *before* it costs a network round-trip.

---

## 5. Architectural patterns

### Two-tier loop (recommended, mirrors GR00T N1)

```
Fast loop  (System-1, phone)        Slow loop  (System-2, phone)
-------------------------           -------------------------
- Camera frame grab @30 fps         - Wake on:
- YOLO/MediaPipe detection            * new high-confidence detection
- Audio VAD + wake-word               * wake-word fired
- IMU echo from ESP32                 * timeout (idle thinking, ~2 s)
- Heuristic safety override         - Build prompt from:
  (e.g. obstacle <30 cm -> stop)      * last 3 keyframes (or text scene)
                                      * recent transcript
                                      * current behavior + state
                                    - Call VLM/LLM (200-1500 ms)
                                    - Parse + validate JSON
                                    - Emit behavior_command via WebSocket

ESP32 brainstem
-------------------------
- Receives JSON commands @1-5 Hz
- Optionally receives binary 50 Hz pose stream during dances
- Runs IMU balance @100+ Hz, servo control @50+ Hz
- Owns emergency stop unconditionally
```

Key principles:

- **Event-driven LLM**, not polling. Idle robot should *not* be running Gemma 3n in a loop — that murders battery (a 4B model at full tilt eats ~5–10 W on a phone). Wake the LLM when the world changes or after an idle timeout.
- **Speculative continuation**: while the LLM is thinking, keep executing the previous behavior smoothly. Never block servos on inference.
- **Cancel-on-staleness**: if a new wake event fires before the prior LLM call returns, cancel the old call and prompt with the fresh context.
- **KV-cache pinning**: load the system prompt + vocabulary + behavior catalog once at app start, keep it warm. New calls only prefill the dynamic suffix.
- **Adaptive cadence**: if the phone is hot or low on battery, drop the VLM cadence (or fall back to "classical CV → text-only Gemma 3 1B" path). The user will not notice — the robot just thinks less.

### When classical CV is enough

Don't burn an LLM call to learn that the floor is in front of you. Use the LLM only when the situation is *genuinely* ambiguous: novel objects, social interaction, a person speaking, a goal that requires planning. Most of the time, a state machine + detection thresholds drives the choreography vocabulary directly.

---

## 6. Latency budget

Realistic end-to-end "camera sees X → first servo motion" on a 2024-class flagship:

| Stage | Time |
|---|---|
| Camera frame to GPU buffer | 15–30 ms |
| Vision preprocess (resize, normalize) | 5–10 ms |
| **VLM image encode (Gemma 3n E2B, 256 tokens)** | 80–200 ms |
| **VLM prefill (sys prompt cached, ~50 new tokens)** | 30–80 ms |
| **VLM decode (~30 tokens output, grammar-constrained)** | 200–600 ms |
| JSON parse + validation | <2 ms |
| WebSocket send (loopback to nearby ESP32) | 5–20 ms |
| ESP32 parse + servo dispatch | 5–15 ms |
| Servo mechanical latency to first detectable motion | 20–50 ms |
| **Total (VLM path)** | **~360 ms – 1.0 s** |
| **Total (classical CV → text-only Gemma 3 1B)** | **~120–350 ms** |
| **Total (classical CV → state machine, no LLM)** | **~50–120 ms** |

This is why the two-tier architecture is non-negotiable: the VLM is ~10× slower than reflexes. The fast loop has to handle anything time-critical.

---

## 7. Recommended stacks (pick one to start, graduate later)

### Path A — "Voice puppy" (minimal, ship in 2 weeks)

**Goal:** robot responds to voice commands, no vision-driven autonomy.

```
Wake word:     Porcupine ("hey walker")
ASR:           Moonshine Tiny (Android: TFLite/ONNX; iOS: CoreML)
LLM:           Apple Foundation Models (iOS) / Gemma 3 1B via MediaPipe (Android)
Output:        Guided generation / GBNF -> {behavior, params}
Transport:     existing WebSocket+JSON to ESP32
```

Data flow: mic → Porcupine → Moonshine streams transcript → on endpoint, LLM call → JSON → validate → WebSocket → ESP32 → servos. Nothing here needs the camera. End-to-end ~400 ms from end of utterance to first motion. Battery cost is negligible (LLM only fires per command).

### Path B — "Watcher" (the sweet spot)

**Goal:** robot reacts to its environment using vision, voice still works.

```
Always-on:     YOLOv8-nano @ 15 fps (MediaPipe Object Detector also fine)
               + Porcupine wake word
               + obstacle/cliff heuristic from detections + IMU
Slow loop:     SmolVLM2 500M OR Moondream 0.5B @ 1 fps (event-triggered)
               via MediaPipe LLM Inference (Android) / Core ML (iOS)
               keyframe + text scene description in prompt
LLM output:    behavior JSON via constrained decoding
ASR (on wake): Moonshine Tiny
Transport:     WebSocket+JSON, plus binary channel during named dances
```

Data flow: classical CV runs continuously and handles "stop/avoid" reflexively. When CV detects a novel scene event (new person, hand wave, unfamiliar object) or a wake-word fires, the slow loop builds a prompt (last 3 keyframes + 30 s text history + transcript if any) and calls the small VLM. JSON behavior comes back, validated, sent to the brainstem. Apparent latency: 50 ms for reflexes, 400–800 ms for "thoughtful" reactions.

### Path C — "Embodied Gemma" (ambitious, demoable)

**Goal:** show off a phone-driven multimodal robot to AI researchers.

```
Single model:  Gemma 3n E2B (text + image + audio) via MediaPipe LLM / LiteRT-LM
Vision:        2 fps frame sampling, 256-token image encoding
Audio:         direct into Gemma 3n (skip separate ASR for short prompts)
               OR Moonshine for long dictation
LLM output:    JSON behavior + reasoning trace
Safety net:    classical CV obstacle/fall detector still runs as a hard override
Transport:     WebSocket+JSON; binary channel for choreographed routines
```

Data flow: Gemma 3n is the brain. It gets a scrolling window of (image, audio chunk, last commands) and emits a behavior every 0.5–1 s. The classical CV layer becomes a safety supervisor only. Phone runs warm (~5 W), battery limits sustained use to ~1–2 h. This is the demo that a researcher will fork.

**My pick for PhoneWalker v0.2:** ship Path A first (it's a complete, satisfying product), then layer Path B on top (reuses everything in A and adds vision). Save Path C for a `--demo-mode` switch.

---

## 8. Known projects and references

- **Droidrun** — LLM-driven Android UI automation. Not a robot, but the prompt-→-action loop, function-calling pattern, and validation layer are directly transferable.
- **LLM-Hub** — open-source Android app for on-device LLM chat, multiple runtimes, NPU acceleration patterns worth lifting. <https://github.com/timmyy123/LLM-Hub>
- **mllm (UbiquitousLearning)** — fast multimodal LLM inference engine specifically for mobile. <https://github.com/UbiquitousLearning/mllm>
- **Google AI Edge Gallery** — official Android reference app for on-device generative AI; useful as a runtime/UX template.
- **HuggingFace SmolVLM2 iPhone demo** — proves a 500M VLM does live video understanding on consumer iPhone.
- **awesome-mobile-llm** — curated list. <https://github.com/stevelaskaridis/awesome-mobile-llm>
- **Stanford Doggo** and **Pupper** — cleanest writeup of the layered control pattern.
- **NVIDIA GR00T N1** — the dual-system (System-2 VLM @ 10 Hz, System-1 action @ 120 Hz) paper is the academic version of what your two-tier loop should be doing.
- **SmolVLA / LeRobot** — HuggingFace's robot policy work, async inference patterns. <https://huggingface.co/blog/smolvla>
- **WhisperKit** — production iOS reference for on-device ASR with ANE acceleration.
- **llama.cpp grammars** — for the GBNF-constrained behavior DSL.
- **Apple Foundation Models** — `@Generable` guided generation is the cleanest structured-output API on any platform right now.

---

## Bottom line

Your existing architecture is already shaped correctly for this — the JSON behavior protocol and choreography vocabulary *are* the action space the brain needs to learn. Don't change them. Build a phone app whose entire job is: **(perception) → (small LLM with constrained JSON output) → (validation) → existing WebSocket**. Start with voice (Path A), add vision (Path B), and keep classical CV running underneath as a safety supervisor regardless of what big model you're running on top.

The single most leverage-y decision you can make right now is **commit to a constrained-output schema today** (define the GBNF grammar / the `@Generable` Swift type / the JSON schema once). Every model you swap in later — Gemma 3n, SmolVLM, Moondream, Apple Foundation, whatever wins next quarter — plugs into the same socket, and the brainstem never knows the difference.
