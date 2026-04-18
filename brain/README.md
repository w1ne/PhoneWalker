# PhoneWalker Brain — Python reference implementation

Runs on a laptop, speaks the firmware wire protocol, and drives the
PyBullet simulator end-to-end. This is the working reference for the
eventual Android brain; it also doubles as the debug/dev loop for the
robot. See `../BRAIN_ARCHITECTURE.md` for the design.

## Quick start

```bash
pip install pytest pytest-asyncio pybullet

python3 -m brain.schema.generate          # regenerate schema + grammar
python3 -m pytest brain/tests/ -v         # 45 tests incl. sim integration
python3 -m brain.main                     # interactive — drives the sim
```

Example:

```
you> please bow
→ bow_front seq=1  brainstem: [{'t': 'ack', 'c': 'pose', 'ok': True}]
you> jump
✗ rejected: busy: previous behavior finishes in 580ms
you> (wait a second)
you> jump
→ jump seq=2  brainstem: [{'t': 'ack', 'c': 'jump', 'ok': True}]
you> ESTOP
→ ESTOP  brainstem: [{'t': 'ack', 'c': 'estop', 'ok': True}]
```

The `busy` rejection is deliberate — a 4-servo robot can only do one
motion at a time. Emergency stops (`ESTOP`, `emergency`, `freeze`, …)
preempt.

## Layout

```
brain/
  schema/
    vocabulary.py            ← source of truth
    generate.py              ← regenerates behavior.schema.json + .gbnf
    behavior.schema.json     ← generated
    behavior.gbnf            ← generated (llama.cpp grammar)
  validator.py               ← parse + clamp + busy-track + stamp
  wire.py                    ← brain → firmware wire format
  transport.py               ← SubprocessBrainstem (PyBullet sim),
                               StdoutBrainstem (dev)
  llm/
    mock.py                  ← rule-based; pass messy=True for real-LLM slop
    llama_cpp_backend.py     ← real LLM via llama-cpp-python + GBNF
  main.py                    ← entry point
  tests/                     ← unit + sim integration (auto-launches sim)
```

## Real LLM (optional)

```bash
pip install llama-cpp-python
python3 -m brain.main --llm llama_cpp \
    --model /path/to/gemma-3-1b-it-Q4_K_M.gguf
```

The GBNF grammar at `brain/schema/behavior.gbnf` makes the model's
output guaranteed-parseable JSON over the allowed behaviors. The
validator still runs (whitelist, clamp, busy check).

## Transports

```bash
python3 -m brain.main                         # default: PyBullet sim
python3 -m brain.main --transport stdout      # print wire format only
python3 -m brain.main --gui                   # sim with pybullet window
```

A real ESP32 serial transport will land when the hardware loop is next
on the roadmap.

## Adding a new pose

1. Add the servo positions to `firmware/src/MotionController.h:POSE_TABLE`
   and `firmware/simulation/sim.py:POSE_TABLE`.
2. Add the name to `brain/schema/vocabulary.py:POSES`.
3. Run `python3 -m brain.schema.generate`.
4. Run `python3 -m pytest brain/tests/` — `test_schema_generation.py`
   catches stale generated files and `test_sim_integration.py` catches
   firmware drift.

## What this doesn't do (yet)

- Real robot over serial.
- Voice input (ASR).
- Camera / vision.
- Queue commands instead of rejecting when busy.
- Use telemetry from the sim/robot to inform the LLM.

Each of these plugs into the existing validator/transport without
changing the brain ↔ firmware contract.
