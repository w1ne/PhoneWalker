# Running the brain on a Pixel (Termux)

Fastest path from "I have a Pixel and a laptop" to "the phone is driving
the robot sim over WiFi." No Android Studio, no MediaPipe SDK, no APK —
just Termux + the same Python brain you already ran on the laptop.

## Prerequisites

- Any Pixel (6 or newer recommended; older Tensor/Snapdragon Pixels work
  but will be slower).
- A laptop on the same WiFi network.
- The PhoneWalker repo cloned on both, or at least the `brain/` and
  `firmware/simulation/` folders.

## Laptop side — sim server

```bash
cd ~/projects/PhoneWalker
pip install pybullet
python3 -m brain.tools.sim_server --host 0.0.0.0 --port 8765
```

Leave it running. It spawns a fresh PyBullet sim per client connection and
bridges TCP ↔ sim stdin/stdout. Note your laptop's LAN IP:

```bash
ip addr | grep 'inet ' | grep -v 127.0.0.1
```

## Phone side — Termux

1. Install **Termux** from F-Droid (do not use the old Play Store build,
   it's abandoned): <https://f-droid.org/en/packages/com.termux/>.
2. In Termux:

```bash
pkg update && pkg upgrade -y
pkg install -y python git clang cmake rust openssl

# Dependencies for llama-cpp-python (local build on the phone)
MATHLIB=m CMAKE_ARGS="-DGGML_NATIVE=ON" \
    pip install --no-cache-dir llama-cpp-python

pip install --no-cache-dir pytest pytest-asyncio

# Get the repo
git clone https://github.com/<you>/PhoneWalker.git   # or rsync / adb push
cd PhoneWalker
```

3. Grab a tiny model:

```bash
mkdir -p models && cd models
curl -L -o qwen2.5-0.5b-instruct-q4_k_m.gguf \
    'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true'
cd ..
```

## Run it

Phone:

```bash
python3 -m brain.main \
    --llm llama_cpp \
    --model models/qwen2.5-0.5b-instruct-q4_k_m.gguf \
    --transport tcp --host <laptop-ip> --port 8765
```

Type commands; they go phone → LLM → validator → wire → laptop sim.

```
you> bow
→ bow_front seq=1  brainstem: [{'t': 'ack', 'c': 'pose', 'ok': True}]
you> jump
→ jump seq=2  brainstem: [{'t': 'ack', 'c': 'jump', 'ok': True}]
you> walk forward
→ walk seq=3  brainstem: [{'t': 'ack', 'c': 'walk', 'ok': True, 'state': 'walking'}]
you> stop
→ stop seq=4  brainstem: [{'t': 'ack', ...}]
you> estop
→ ESTOP  brainstem: [{'t': 'ack', 'c': 'estop', 'ok': True}]
```

If you want to skip the LLM (to confirm the wire is healthy), drop
`--llm llama_cpp --model ...` — the default mock LLM covers the core
keywords.

## Realistic Pixel performance

Qwen2.5-0.5B Q4_K_M, llama.cpp with default build, CPU only:

| Device | tok/s decode | ~latency per command |
|---|---|---|
| Pixel 9 Pro (Tensor G4) | 15–25 | 1.5–2.5 s |
| Pixel 8 / 8 Pro (Tensor G3) | 12–20 | 1.8–3 s |
| Pixel 7 / 7 Pro (Tensor G2) | 8–14 | 2.5–4 s |
| Pixel 6 (Tensor G1) | 5–10 | 3–6 s |

Later, rebuilding llama-cpp-python with `GGML_CPU_KLEIDIAI=ON` in
`CMAKE_ARGS` can cut this significantly on Tensor G3/G4. Not essential
for first light.

## When the real robot arrives

Replace the laptop-side `sim_server.py` with:

* **USB OTG**: phone → USB-C OTG → ESP32. Needs a small Termux serial
  bridge, TBD.
* **WiFi JSON server on the ESP32**: firmware side is deferred
  (see `BRAIN_ARCHITECTURE.md` §4). When it lands, point
  `--host/--port` at the ESP32 directly and drop the laptop from the
  loop.

## Troubleshooting

- `llama-cpp-python` build fails on Termux: install rust/clang/cmake
  first; the build is CPU-bound and takes ~10–20 min on a Pixel.
- `connection refused`: check the laptop's firewall lets port 8765 in
  on the WiFi interface, and that the phone and laptop are on the same
  subnet.
- `busy: previous behavior finishes in Nms`: the busy tracker is working
  as designed — the robot can only do one motion at a time. Wait or
  send `estop` (or say "freeze", "halt", "panic").

## Why not a native Android app?

We'll build one eventually (see `mobile/README.md`). It isn't needed for
the demo: Termux + Python covers voice-free Path A today, and the port
to Kotlin + MediaPipe LLM Inference is a 1:1 translation of the same
schema/validator/wire/transport once we want voice, tighter integration
with phone sensors, or on-screen UI.
