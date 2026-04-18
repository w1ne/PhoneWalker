# Robotics Architecture in 2026: A Reference Document for PhoneWalker

*Compiled April 2026. Purpose: honest survey of how intelligent robots are actually built today, so PhoneWalker's architecture is grounded in real robotics practice rather than web-agent thinking.*

---

## 1. The Real Architecture Stack of Modern Intelligent Robots

Every serious humanoid/quadruped platform shipping in 2025–2026 is running some variant of a **hierarchical dual- (or triple-) rate stack**. The pattern is remarkably consistent across companies:

| Layer | Rate | Job | Typical model |
|---|---|---|---|
| High-level reasoning / planner | 1–10 Hz | language understanding, task decomposition, spatial reasoning, tool use | VLM or "ER" (embodied-reasoner) model — Gemini Robotics-ER 1.5, GPT-class LLM, Helix System 2 |
| Mid-level policy (VLA) | 20–50 Hz | vision + language + proprioception → action chunks | π0 / π0.5, Gemini Robotics 1.5, GR00T N1.5/N2, Helix System 1, OpenVLA, RDT-1B, SmolVLA |
| Low-level controller | 200–1000 Hz | balance, joint torques, safety limits, contact | MPC, whole-body QP, impedance control, learned RL locomotion policy |

### Concrete instantiations

- **Figure 02 / Helix** — explicitly described as dual-system: System 2 (internet-pretrained VLM) at **7–9 Hz** emits a latent semantic vector, System 1 (visuomotor transformer) at **200 Hz** emits joint commands. This is a deliberate mirror of Kahneman "think fast / think slow."
- **Gemini Robotics 1.5** (DeepMind, Oct 2025) — two separate models. **Gemini Robotics-ER 1.5** is the orchestrator (planning, grounding, progress estimation, tool calls — including web search). **Gemini Robotics 1.5** is the VLA executor with interleaved natural-language "thinking tokens" before action chunks. A novel Motion Transfer mechanism lets one checkpoint drive ALOHA, Bi-arm Franka, and Apollo humanoid from the same weights. ([arXiv 2510.03342](https://arxiv.org/abs/2510.03342), [DeepMind](https://deepmind.google/models/gemini-robotics/))
- **Physical Intelligence π0 / π0.5** — VLA with a **flow-matching action head** emitting continuous action chunks at **~50 Hz**. π0.5 (Sep 2025) adds two-stage training: pretrain with FAST discrete-token tokenizer on heterogeneous data (multiple robots + web + "high-level semantic action prediction"), then post-train with flow matching for high-frequency dexterity. The ["knowledge insulation"](https://www.physicalintelligence.company/download/pi05_KI.pdf) paper is worth reading. ([π0.5 PDF](https://www.pi.website/download/pi05.pdf))
- **NVIDIA GR00T N1 → N1.5 → N1.6/N2** — open-weights humanoid foundation VLA. N1.5 outperformed N1 ~3× on DreamGen tasks (38.3% vs 13.1%). N2 is a "world-action model" built on DreamZero, claiming >2× success over leading VLAs. Reference platform: Fourier GR-1, Unitree G1. ([GR00T N1.5](https://research.nvidia.com/labs/gear/gr00t-n1_5/), [Isaac-GR00T GitHub](https://github.com/NVIDIA/Isaac-GR00T))
- **1X NEO / Redwood** — single unified VLM running on NEO's embedded GPU, **~160 M parameters at 5 Hz**, coordinated whole-body (mobile manipulation + locomotion). Paired with a separate "1X World Model" used offline for policy evaluation and data augmentation. ([Redwood AI](https://www.1x.tech/discover/redwood-ai-world-model))
- **Boston Dynamics Atlas** — the most "hybrid" stack. Classical MPC + whole-body QP controller still runs the low level; a **diffusion-transformer VLA at 30 Hz** (images + proprioception + language → actions, trained with flow-matching loss) now rides on top, co-developed with Toyota Research Institute as a "Large Behavior Model." BD is explicitly partnering with the Robotics and AI Institute to use RL to improve the VLA. ([BD blog](https://bostondynamics.com/blog/large-behavior-models-atlas-find-new-footing/))
- **Unitree G1 / Tesla Optimus** — learned locomotion policies (RL in Isaac Lab / MuJoCo) for the low level, increasingly VLA-driven manipulation on top. Unitree ships `unitree_rl_gym` as the reference pipeline.

### What VLAs output

Varies, and this is architecturally important:
- **Discrete action tokens** (RT-2, OpenVLA, π0-FAST) — autoregressive, simple to train, slow at inference.
- **Continuous action chunks via flow matching / diffusion** (π0, π0.5, Atlas LBM, RDT-1B) — emits N future timesteps (chunks of 10–50 actions) in one forward pass. This is how you get 50–200 Hz effective output from a 5–10 Hz VLM — you run the VLM once, then execute the chunk.
- **Latent vector → downstream fast policy** (Helix) — System 2 passes embeddings, not commands.

The dominant 2026 paradigm is **action-chunked flow-matching/diffusion VLAs**. Pure autoregressive token VLAs are on the way out for dexterity-critical work.

### How language grounds to action

Three patterns exist, and real systems mix them:

1. **End-to-end VLA**: language in the prompt → action out. Works for short instructions like "pick up the red cup." This is π0, OpenVLA, SmolVLA.
2. **LLM/VLM plans → VLA executes skills** (SayCan lineage, Gemini Robotics 1.5's ER↔VLA, Figure's S2→S1). "Walk to the red chair and sit" decomposes into `navigate_to(red chair)` + `execute_skill(sit)` where each is a VLA rollout. This is the current state-of-the-art for long-horizon tasks.
3. **LLM picks from pre-defined skill library with affordance scoring** (classic SayCan). Still used in production robots with reliable, hand-authored skills; less trendy but more debuggable.

---

## 2. Perception — What "Vision" Actually Means on a Robot

"Call a VLM on a frame every second" is not robot perception. Real stacks are layered:

### Geometric / metric layer
- **Visual-inertial SLAM**: `ORB-SLAM3`, `RTAB-Map` (both still ubiquitous in ROS 2). NVIDIA's **cuVSLAM** (inside Isaac Perceptor) is the GPU-accelerated default on Jetson. **Kudan Visual SLAM** is the 2025 commercial favorite integrated with Isaac Perceptor.
- **Learning-based SLAM**: `DROID-SLAM` for offline/high-quality, and in 2025 **VGGT** (Visual Geometry Grounded Transformer) — a 3D foundation model that jointly predicts pose + intrinsics + dense geometry from raw images, calibration-free.
- **Dense 3D**: `nvblox` (TSDF on GPU, inside Isaac Perceptor) for occupancy + 3D scene reconstruction. Gaussian Splatting is creeping in for photometric scene reconstruction but not yet a live-SLAM default.

### Semantic layer (open-vocabulary)
- **Detection**: `YOLO-World` (52 FPS on V100, open-vocab via CLIP), `OWL-ViT`/`NanoOWL` (NanoOWL is the Jetson-optimized TensorRT variant — fastest on edge).
- **Segmentation**: `SAM 2`, `EfficientViT-SAM`, `NanoSAM`. Usually fed bounding boxes from a detector (Grounded-SAM pattern).
- **Grounded-SAM-2**: Grounding DINO + SAM 2 for open-vocab track-anything — the 2025 go-to for "find the thing I named and keep a mask on it."

### Spatial-semantic memory (this is what replaces "vector-DB memory")
- **ConceptGraphs** (CoRL 2024) — open-vocabulary 3D scene graph, objects as nodes w/ CLIP embeddings, LLM-generated relations as edges.
- **HOV-SG** (RSS 2024) — hierarchical: floor → room → object, each with open-vocab features. Used for queries like "the coffee cup in the kitchen on the second floor." 75% smaller than dense open-vocab maps. ([hovsg.github.io](https://hovsg.github.io/))
- Dynamic open-vocab scene graphs for long-term mobile manipulation (2024–2025) are an active research front.
- Yes — language grounds directly into this. "The red mug by the sink" is answered by traversing the graph (room=kitchen, object=mug, relation=near(sink), color=red), not by stuffing an image into a VLM every cycle.

### Active perception
Actively commanded head/gaze is coming back — Helix, Gemini Robotics, and Atlas all do it implicitly via VLA outputs (neck joints are part of the action space). For quadrupeds with a pan/tilt head it's the same story: the VLA decides where to look.

---

## 3. Memory in Real Robots vs. Memory in Chatbots

Chatbot memory (Letta, mem0, vector recall of past messages) is **not** what robots do. Robot memory is typed:

| Type | What it stores | Real-robot implementation |
|---|---|---|
| **Spatial / semantic map** | "where things are" | 3D scene graph (ConceptGraphs, HOV-SG), TSDF + labels, occupancy grids |
| **Episodic** | "what happened last time I tried X" | Trajectory buffers (often just the teleop/autonomous dataset); research: MemoryVLA, EchoVLA |
| **Procedural / skills** | "how to do X" | Learned policy weights, skill libraries, motion primitives |
| **Semantic / world knowledge** | "cups contain liquid" | The VLM/LLM's pretraining |
| **Working / short-term** | "what I just saw 3 seconds ago" | VLA context window, observation history buffer |

Notable 2025 work:
- **MemoryVLA** (arXiv 2508.19236) — dual working-memory + "hippocampal" episodic memory inside a VLA. +26 points on long-horizon tasks over baselines.
- **EchoVLA** (arXiv 2511.18112) — separate scene memory (spatial) and episodic memory (task-level multimodal) as declarative memory modules.
- **Gemini Robotics-ER 1.5** — has an explicit "thinking + memory" reasoning path that persists across steps in a long task.

The takeaway: **memory in robots is structured and typed by function**, not a flat "chat history." If you build PhoneWalker memory as `{spatial_map, recent_episodes, known_skills}` rather than `conversation[]`, you're aligned with real practice.

---

## 4. Frameworks and Substrates

### ROS 2 — still the default middleware
- **Nav2** (`navigation.ros.org`) is the stack for mobile robots — it explicitly supports legged base types, runs behavior trees (BehaviorTree.CPP v4) as the task executor, and is used by essentially every indoor AMR including quadrupeds. ([Nav2 docs](https://docs.nav2.org/))
- **MoveIt 2** for arms; less relevant for a 4-servo quadruped without a manipulator.
- **BehaviorTree.CPP** is the de-facto task-orchestration library. Nav2 uses it internally; many humanoid control stacks use it at the top level.
- A 2025 University of Agder project shipped a full ROS 2 + Nav2 + SLAM Toolbox quadruped stack — this is the template.

### LeRobot (Hugging Face) — the hobbyist/research VLA stack
This is the project to know. `v0.5.0` (late 2025/early 2026) adds:
- Full Unitree G1 humanoid whole-body control support.
- `Pi0-FAST` autoregressive VLA + **Real-Time Chunking** for responsive inference.
- Streaming video encoding for dataset collection.
- Integration with NVIDIA Isaac Lab Arena.
- **SmolVLA** (450 M params, MIT-licensed, trained only on community-shared LeRobot-tag datasets) — runs on a **MacBook or single consumer GPU**, matches much larger proprietary VLAs. This is the single most important model for hobbyists. ([SmolVLA blog](https://huggingface.co/blog/smolvla), [lerobot/smolvla_base](https://huggingface.co/lerobot/smolvla_base))

LeRobot is aimed squarely at hobbyists and researchers. It's what SO-100/SO-101 (the $100 manipulator arm) runs on. It does **not** yet have a turnkey quadruped controller like CHAMP — but you can train a locomotion policy in Isaac Lab and deploy through LeRobot.

### NVIDIA Isaac Lab / Isaac Sim / GR00T
- **Isaac Lab** is the current standard for RL-based locomotion/manipulation training. GPU-parallelized, multiple physics backends (PhysX, Newton, Warp, MuJoCo). Used to train Spot, Unitree, GR-1.
- Boston Dynamics + NVIDIA + RAI Institute jointly shipped the **RL Researcher Kit** that deploys Isaac-Lab-trained policies to real Spot with joint-level control + onboard Jetson AGX Orin. This is the reference workflow.
- Assumed hardware: Jetson Orin Nano (40 TOPS, $250–$500) for edge, AGX Orin for serious onboard compute, or off-board desktop RTX.

### Hobbyist quadruped stacks
| Project | Locomotion | Brain | Status |
|---|---|---|---|
| **Petoi Bittle / BiBoard** | Hand-tuned gait, on ESP32 | External (phone/PC/LLM via serial) | Shipping, 9-DOF, ~$300. OpenCatGym adds RL. |
| **MangDang Mini Pupper 2/3** | PID + gait engine on Raspberry Pi | Pi + optional LLM integration (docs ship ChatGPT/Gemini/Claude examples) | Shipping, ROS 2, ~$500 |
| **Stanford Pupper v3** | Torque-controlled brushless motors, RL policy option | Raspberry Pi 5, camera; used in CS 123 | Open-sourced 2025, ~$1500 kit |
| **CHAMP** | MIT Cheetah hierarchical controller (ROS 1, ROS 2 ports exist) | Any ROS host | Mature, Anymal/Spot/Go2 configs available |
| **Unitree Go2 EDU** | Factory RL policy + `unitree_rl_gym` | Onboard Jetson Orin Nano 8 GB | Turnkey, ~$2800–$6000 |
| **Pupper v3 + SmolVLA** | RL policy | Pi 5 + SmolVLA for command→action | Achievable today |
| **OpenCat / OpenCatGym** | Learned gait in sim → ESP32 | External | Mature codebase |

**CHAMP** is the controller most serious hobbyists should copy for the low level if they're building custom hardware. **Nav2** is the autonomy stack on top.

### Autoware / Nav2 for indoor
- **Autoware** is for self-driving cars. Don't use it for an indoor quadruped.
- **Nav2** is the correct answer.

---

## 5. The Integrated "See, Hear, Remember, Act" Stack (2026 PhD Student Build)

Shortest honest path on reasonable hardware:

**Compute**: Jetson Orin Nano Super 8 GB (40 TOPS, ~$250) is the minimum for on-robot VLA. Jetson Orin NX 16 GB or AGX Orin if you want headroom. Alternatively: off-board workstation with RTX 4070+, robot streams sensors over Wi-Fi 6/5 GHz (adds 20–50 ms latency — tolerable for everything except balance).

**Voice in**: **Moonshine v2** (streaming encoder ASR, 5× faster than Whisper-tiny, runs on Pi). Wake word: `openWakeWord` or ESP32-S3 local wake-word via TFLite Micro. ([Moonshine GitHub](https://github.com/moonshine-ai/moonshine))

**Perception**:
- Geometry: Isaac Perceptor (cuVSLAM + nvblox) on Jetson, or RTAB-Map if Jetson-less.
- Open-vocab detection: `NanoOWL` (TensorRT, Jetson-optimized) → `NanoSAM` for masks.
- Spatial memory: ConceptGraphs-style scene graph, updated at ~1 Hz.

**Hierarchical control**:
- High-level: Gemini Robotics-ER 1.5 via API, or local Qwen2.5-VL / Gemma-3 for offline.
- Mid-level: SmolVLA (450 M, fits on Jetson) or π0.5 via openpi if you have the compute.
- Low-level: RL locomotion policy (trained in Isaac Lab) at 50–200 Hz on microcontroller / Jetson CPU side.

**Memory**:
- Spatial: HOV-SG / ConceptGraphs backed by SQLite + vector store.
- Episodic: LeRobot dataset format (parquet + mp4), append per task.
- Procedural: named skill registry (YAML + policy checkpoints).

**Voice out**: **Piper TTS** (CPU, real-time on Pi) or **Kokoro-82M** (100× real-time on GPU). ([Piper](https://github.com/rhasspy/piper))

**Safety**: hard-coded rate limits and workspace bounds at the low-level controller; a watchdog that kills torque on comms loss; an "estop topic" in ROS that any node can publish to. **Never** trust the VLA to enforce safety — it's probabilistic.

---

## 6. Where LLMs and Agent Frameworks Actually Fit

**Honest answer**: in production robots, LLMs live in **exactly three** places:

1. **The high-level planner / orchestrator** — "make me breakfast" → ordered sequence of parameterized skill calls. This is Gemini Robotics-ER, the `think` layer of π0.5, Helix System 2. Typically runs 1–10 Hz.
2. **A scene-reasoning module** — VQA over current observation, "is the door open?", "which drawer has the spoons?". Can be the same model as (1).
3. **The chit-chat / voice UX** — whatever the user talks to. Often decoupled from (1) for latency, though Gemini Robotics 1.5 merges them.

LLMs are **not** driving joints. The VLA does. And the VLA is not a generic LLM — it's a language model with an action head, typically initialized from a small VLM (SigLIP/DINOv2 + Gemma/Llama-2-class) and trained on robot trajectories.

**Agent frameworks (LangGraph, smolagents, OpenHands, Letta) are essentially absent from real robotics.** The ER-VLA split in Gemini Robotics 1.5 is "agentic" in spirit — the ER model can call web search as a tool — but it's not built on a web-agent framework. The reasons are: (a) latency budgets, (b) determinism/safety, (c) the "tools" are robot skills with rich state, not REST endpoints.

**MCP in robotics**: early but real. The 2026 MCP roadmap explicitly calls out robotics/embodied use cases. There's a `ROSBag MCP Server` (arXiv 2511.03497) for LLM-driven log analysis. Expect MCP to appear as the **developer-tool layer** (introspecting the robot, querying its state from an LLM IDE) long before it's in the live control loop.

**Implication for PhoneWalker**: if you reach for LangGraph/Letta/MCP-tools for the core control loop, you're building a web agent with servos attached. The honest pattern is: voice → planner (LLM) → skill selector → VLA or hand-coded skills → low-level gait controller.

---

## 7. Hobbyist-Scale Reality Check for a $300 4-Servo Quadruped

**Honest truth**: a 4-servo quadruped is **below** the complexity threshold where a VLA adds value. A VLA outputs joint-angle deltas over many DOFs; with 4 DOFs you mostly need a **gait engine** (12 named gaits, parameterized by speed/direction) not a neural policy.

What matches the scale:

| Capability | Sensible choice |
|---|---|
| Locomotion | Hand-tuned/IK gait engine on ESP32 (à la OpenCat). Learned policy is overkill at 4 DOF. |
| Voice in | Phone app does ASR (Moonshine or cloud), sends intents over BLE/Wi-Fi to ESP32. |
| Perception | Phone camera or USB cam on phone/PC, YOLO-World or Gemini-Flash vision on the phone. |
| Planner | LLM on phone/PC — Gemini Flash, Claude Haiku, or local Gemma-3-4B. |
| Skills | Named intents: `sit`, `walk_forward(speed, duration)`, `turn(angle)`, `dance`, `look_at(x,y)`. |
| Memory | SQLite with a small scene graph (rooms, landmarks) + episode log. |
| TTS | Piper on phone/PC. |

**Projects to actually copy from, ranked by relevance**:

1. **Petoi OpenCat / OpenCatEsp32** ([GitHub](https://github.com/PetoiCamp/OpenCatEsp32)) — closest existing system to PhoneWalker. ESP32, servo quadruped, Arduino-style firmware with named commands, documented ChatGPT integration examples. *Start here.*
2. **MangDang Mini Pupper 2** — if you can afford Pi + lidar, their ROS 2 + LLM example code is directly reusable.
3. **LeRobot SO-100/SmolVLA** — not locomotion, but the right reference for how a hobbyist VLA stack is actually built, if you ever add an arm.
4. **CHAMP** — if you ever upgrade to 12 DOF with torque-capable actuators.
5. **Stanford Pupper v3** — aspirational; their CS 123 curriculum is public and worth reading.

**What to absolutely not reinvent**: SLAM, open-vocab detection, ASR, TTS, behavior-tree engines, the gait engine. Every single one of these has a mature library.

---

## 8. Concrete Architecture Options for PhoneWalker

### Option A — "Serious/expensive" (~$600–$900, 2–3 month build)

**Hardware**: upgrade to a Jetson Orin Nano Super 8 GB onboard + ESP32 as the servo driver. Add a global-shutter camera + IMU.

**Stack**:
- **Middleware**: ROS 2 Jazzy on Jetson, micro-ROS bridge to ESP32.
- **Low-level**: ESP32 runs a CHAMP-style gait engine (port / adapt from OpenCat); subscribes to `/cmd_vel` and joint targets.
- **Locomotion policy (optional)**: train an RL policy in Isaac Lab for 4-DOF gait, deploy via ONNX on Jetson — only if you want dynamic behavior. Otherwise the hand-coded gait is fine.
- **Perception**: Isaac Perceptor (cuVSLAM + nvblox) + NanoOWL for open-vocab detection.
- **Spatial memory**: ConceptGraphs-style scene graph in SQLite.
- **Planner**: local Gemma-3-4B or Qwen2.5-VL-7B, with a small skill library exposed as function-call schemas (not MCP — direct JSON).
- **VLA (optional)**: SmolVLA fine-tuned on your teleop data, for any manipulation if you add a gripper.
- **Nav**: Nav2 with a legged-base config.
- **Voice**: Moonshine v2 (ASR) + Piper (TTS) onboard.

Off-the-shelf: everything above. Custom: gait engine tuning, skill library, ConceptGraph integration glue.

### Option B — "Realistic hobbyist" (target budget, no GPU on robot)

**Hardware**: ESP32 + 4 servos on the robot. Phone or laptop nearby runs the brain.

**Stack**:
- **Robot firmware**: fork OpenCatEsp32. Expose a small, strongly-typed command interface over BLE or Wi-Fi: `walk(vx, vy, wz, duration)`, `pose(name)`, `look_at(yaw, pitch)`, plus telemetry: IMU, servo load, battery.
- **Phone/laptop brain** (Python or Kotlin/Swift):
  - ASR: Moonshine v2 (on-device on phone).
  - VLM/LLM: Gemini 2.5 Flash or Claude Haiku via API for the planner — cheap, fast, no infra. With prompt caching the system-prompt+skill-library stays cached cross-turn.
  - Perception: phone camera → YOLO-World or Gemini vision for "what's that" queries.
  - Memory: a small JSON/SQLite scene graph (rooms, objects, last-seen pose) — not a chat log.
  - Skill selector: a function-calling loop that picks `walk/pose/look_at/speak/query_scene` and observes results. Keep the tool set *small* (5–8 tools). This is the one place agent-framework patterns fit cleanly.
  - TTS: Piper or Kokoro on phone/laptop.
- **No ROS, no VLA, no RL policy** — unnecessary at this scale.

Off-the-shelf: OpenCat firmware, Moonshine, Piper/Kokoro, Claude/Gemini API, YOLO-World. Custom: phone app, command protocol, skill library, scene-graph persistence.

**This is the option I'd recommend.** It's honest to the hardware, borrows from real robotics (typed skills, typed memory, structured perception) without pretending to run a VLA on an ESP32.

### Option C — "Lab demo" (flashy, leverage cloud)

**Hardware**: same as B.

**Stack**:
- Stream robot camera + mic to a workstation or cloud.
- Use **Gemini Robotics-ER 1.5** (via API) as the orchestrator — it natively does spatial grounding, progress estimation, and can call tools. It's the closest thing to a hosted "robot brain" that exists today. ([ai.google.dev/robotics](https://ai.google.dev/gemini-api/docs/robotics-overview))
- Expose PhoneWalker's skills (`walk`, `pose`, `look_at`, `speak`) as ER tool calls.
- For the "wow" factor: let ER decompose long commands like "go find my keys and tell me which room they're in." It will plan, call skills, observe, update, and narrate.
- Piper/Kokoro TTS for the response.

Off-the-shelf: everything except the tool-to-robot bridge. Custom: ~200 lines of glue code.

This will be the most *impressive* demo per line of code, and the most dependent on a cloud API. Good for showing people; not good as an identity.

---

## Recommendation

Go with **Option B as the core product**, with an easy path to **Option C as a demo mode** (swap the local LLM planner for Gemini Robotics-ER, same tool interface). This gets you:

- Honest alignment with how hobbyist robots actually work (OpenCat + phone brain + typed skills).
- Real robotics concepts in the architecture (hierarchical control, typed memory, skill library, behavior-tree-ish planner) without LARP'ing as a humanoid lab.
- A credible upgrade path to Option A when the robot grows to 12 DOF.
- Zero dependence on a "web-agent with memory" framing. The LLM is specifically the high-level planner that picks skills — which is exactly its role in Gemini Robotics, Figure Helix, and SayCan.

What to **not** do: build PhoneWalker around a generic agent framework (LangGraph, Letta, smolagents) with a `send_behavior` tool and a vector-DB memory. That's not how robots are built, and the failure modes (unbounded latency, brittle tool loops, no safety layer, unstructured memory) will bite you immediately.

---

## Key References

- Gemini Robotics 1.5: [arXiv 2510.03342](https://arxiv.org/abs/2510.03342), [DeepMind model page](https://deepmind.google/models/gemini-robotics/), [API docs](https://ai.google.dev/gemini-api/docs/robotics-overview)
- π0 / π0.5: [π0.5 PDF](https://www.pi.website/download/pi05.pdf), [openpi GitHub](https://github.com/Physical-Intelligence/openpi), [HF blog](https://huggingface.co/blog/pi0)
- GR00T: [GR00T N1.5](https://research.nvidia.com/labs/gear/gr00t-n1_5/), [Isaac-GR00T GitHub](https://github.com/NVIDIA/Isaac-GR00T)
- Figure Helix: [Helix announcement](https://www.figure.ai/news/helix), [Helix 02](https://www.figure.ai/news/helix-02)
- 1X NEO Redwood: [Redwood AI](https://www.1x.tech/discover/redwood-ai-world-model)
- Boston Dynamics LBM: [LBM + Atlas](https://bostondynamics.com/blog/large-behavior-models-atlas-find-new-footing/)
- OpenVLA: [arXiv 2406.09246](https://arxiv.org/abs/2406.09246), [openvla.github.io](https://openvla.github.io/)
- SmolVLA: [HF blog](https://huggingface.co/blog/smolvla), [model](https://huggingface.co/lerobot/smolvla_base)
- LeRobot: [v0.5.0 release](https://huggingface.co/blog/lerobot-release-v050)
- HOV-SG: [hovsg.github.io](https://hovsg.github.io/), [arXiv 2403.17846](https://arxiv.org/abs/2403.17846)
- ConceptGraphs: [concept-graphs.github.io](https://concept-graphs.github.io/)
- MemoryVLA: [arXiv 2508.19236](https://arxiv.org/abs/2508.19236)
- EchoVLA: [arXiv 2511.18112](https://arxiv.org/abs/2511.18112)
- Isaac Lab: [GitHub](https://github.com/isaac-sim/IsaacLab), [Spot sim-to-real](https://developer.nvidia.com/blog/closing-the-sim-to-real-gap-training-spot-quadruped-locomotion-with-nvidia-isaac-lab/)
- Isaac Perceptor: [developer page](https://developer.nvidia.com/isaac/perceptor)
- Nav2: [docs](https://docs.nav2.org/)
- CHAMP: [GitHub](https://github.com/chvmp/champ)
- Petoi OpenCat: [OpenCatEsp32](https://github.com/PetoiCamp/OpenCatEsp32)
- MangDang Mini Pupper: [GitHub](https://github.com/mangdangroboticsclub/QuadrupedRobot)
- Stanford Pupper v3: [pupper info](https://robotsthatexist.com/robots/pupper-v3), [Stanford Student Robotics](https://stanfordstudentrobotics.org/pupper)
- Unitree RL Gym: [GitHub](https://github.com/unitreerobotics/unitree_rl_gym)
- Moonshine: [GitHub](https://github.com/moonshine-ai/moonshine)
- Piper TTS: [GitHub](https://github.com/rhasspy/piper)
- YOLO-World: [arXiv 2401.17270](https://arxiv.org/abs/2401.17270)
- Grounded-SAM-2: [GitHub](https://github.com/IDEA-Research/Grounded-SAM-2)
- ROSBag MCP Server: [arXiv 2511.03497](https://arxiv.org/abs/2511.03497)
- MCP 2026 Roadmap: [blog.modelcontextprotocol.io](https://blog.modelcontextprotocol.io/posts/2026-mcp-roadmap/)
- SayCan: [say-can.github.io](https://say-can.github.io/)
