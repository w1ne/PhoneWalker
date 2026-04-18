# PhoneWalker Brain Architecture

Status: **Python reference working end-to-end against the PyBullet sim.**
Real ESP32 hardware loop, Android port, and LLM integration are not yet
wired. See `PHONE_BRAIN_RESEARCH.md` for the model-and-runtime survey that
motivated the design choices here.

Companion docs:
- `BRAIN_BRAINSTEM_ARCHITECTURE.md` — the original aspirational design doc.
  Its big-picture shape (brain/brainstem split, two-tier loop, emergency
  priority) still holds; specifics below supersede it where they conflict.
- `CHOREOGRAPHY_GUIDE.md` — the pose vocabulary the brain speaks to.
- `firmware/src/CommandProcessor.h` — **the actual wire protocol**. This
  file is the ground truth; everything else aligns to it.

---

## 1. The socket

The brain emits readable, LLM-friendly JSON. A thin translator converts it
to the firmware's compact wire format. Two layers, two schemas, one
contract:

```
brain command (LLM-friendly)              firmware wire (what ESP32 parses)
─────────────────────────────             ────────────────────────────────
{                                         {"c":"pose","n":"bow_front","d":1800}
  "v": 1,                            ──►  {"c":"walk","on":true,"stride":150,"step":400}
  "behavior": "bow_front",                {"c":"jump"}
  "params": {"speed": 1800},              {"c":"estop"}
  "seq": 42, "ts_ms": ...                 {"c":"stop"}
}
```

Keeping these separate means:

* The LLM output schema can evolve without touching firmware.
* New models and perception paths plug into the same brain socket.
* Wire compression and firmware compatibility are a transport concern,
  not an AI concern.

The translator lives in `brain/wire.py` and is round-trip tested against
the real `firmware/simulation/sim.py`.

---

## 2. Action space (aligned to the firmware that actually exists)

The earlier draft of this doc listed `walk_forward`, `walk_backward`,
`turn_left`, `turn_right` — the firmware doesn't expose them. The actual
vocabulary:

| Behavior | Firmware command | Notes |
|---|---|---|
| `neutral`, `bow_front`, `lean_left`, `lean_right`, `stretch_diagonal1`, `stretch_diagonal2`, `twist_front_left`, `twist_front_right` | `{"c":"pose","n":"<name>","d":<speed>}` | The 8 poses in `MotionController.h` |
| `walk` | `{"c":"walk","on":true,"stride":N,"step":N}` | Continuous gait |
| `jump` | `{"c":"jump"}` | One-shot |
| `stop` | `{"c":"walk","on":false}` then `{"c":"pose","n":"neutral"}` | Stops gait, returns to centre |
| `estop` | `{"c":"estop"}` | Cuts torque; preempts everything |

No `play_dance` / `play_choreography` in v1. Choreographies are
phone-side — the brain expands them into a sequence of pose commands.

Adding a new behavior requires two changes: a pose row in
`MotionController.h` (and the sim's pose table) and an entry in
`brain/schema/vocabulary.py`. The schema regen + sim-integration test
together catch drift.

---

## 3. Validator (the one mandatory layer)

```
LLM raw text
  │
  ├─ strip markdown fences
  ├─ extract first balanced {...}   ← tolerates prose & extra keys
  │
  ▼
[1] JSON parse
[2] Schema check: v == 1, behavior is a string
[3] Whitelist: behavior ∈ brain's allowed set
[4] Clamp: numeric params to physically safe ranges
[5] Drop unknown top-level and params fields (log, don't fail)
[6] Busy check: reject if the previous behavior is still executing
                (estop always preempts)
[7] Stamp seq + ts_ms, update busy window
  │
  ▼
wire translator → Brainstem transport
```

### The busy tracker (what replaced the earlier rate-limit theater)

Each non-continuous behavior declares an expected completion time from
`duration_ms + hold_ms` (or a per-behavior default in `vocabulary.py`).
New non-emergency commands that arrive before that window closes are
rejected with `busy: NNNms remaining`. This models what a single 4-servo
robot can physically do — one motion at a time — and is the behavior the
LLM needs to learn around.

Exceptions:
* `walk` is continuous; busy window is 0 so `stop` / `estop` /
  pose-change commands apply immediately.
* `estop` always preempts and resets the busy window.

### Robustness to real LLM output

The validator accepts:
* Markdown code fences: `` ```json\n{...}\n``` ``
* Prose around the JSON: `Sure, here: {...} — good luck!`
* Unknown top-level fields (`confidence`, `thought`, …) — logged, stripped.
* Unknown params fields — same treatment.

It rejects:
* Unknown `behavior` values (the core safety gate).
* Wrong schema version.
* Malformed numbers or transitions.
* Any input with no parseable JSON object.

Constrained decoding (llama.cpp GBNF) makes most of the tolerance
unnecessary, but an unconstrained runtime (MediaPipe today) still works.

---

## 4. Transports

| Transport | Use | Status |
|---|---|---|
| `SubprocessBrainstem` | launches `firmware/simulation/sim.py` over stdin/stdout | ✅ working, in CI |
| `StdoutBrainstem` | prints wire messages to stdout for demos | ✅ |
| Serial ESP32 | real robot over USB | TODO |
| WebSocket (phone↔ESP32 WiFi) | Android app target | Deferred until firmware WS server lands |

The earlier design assumed WebSocket everywhere. In reality the current
firmware exposes a serial JSON protocol; the sim matches it bit-for-bit,
which is why the sim is the CI target. WebSocket arrives when the
firmware side does.

---

## 5. Emergency stop — what's actually in place

Three layers were promised originally. Honest status:

1. ✅ **Text-layer bypass.** Transcripts containing `estop`, `emergency`,
   `freeze`, `halt`, `abort`, `kill`, `panic` skip the LLM and emit
   `estop` directly. Implemented in `brain.validator.is_emergency_transcript`.
   The word `stop` is *not* on this list — it's a normal behavior
   (return-to-neutral), not an emergency.
2. ❌ **Fast-loop reflexes** (IMU / obstacle / fall detection). Not
   implemented — requires vision + IMU echo + a real robot. Path B scope.
3. ✅ **Firmware watchdog.** Exists in `firmware/src/SafetySystem.h`. Runs
   independently of the brain. This is the real safety net.

The phone-side `estop` path is convenience; the firmware's watchdog is
authority. Do not confuse the two.

---

## 6. Perception pipelines — still on paper

The research report (`PHONE_BRAIN_RESEARCH.md`) and the original
architecture doc describe the two-tier loop (fast classical CV, slow VLM).
None of this is implemented yet. Path A (voice + text LLM) is the only
thing the current code targets.

When we get to it, the perception layer plugs into the brain by calling
the same validator with a behavior JSON — no other changes needed.

---

## 7. Staged rollout

| Path | Scope | Status |
|---|---|---|
| **A.0 Schema-first** | JSON schema + GBNF + validator + wire translator + sim round-trip | ✅ done |
| **A.1 Real LLM** | swap `MockLLM` for `LlamaCppLLM` with Gemma 3 1B + GBNF | wired; needs a GGUF model to run |
| **A.2 Voice input** | Moonshine Tiny (or SFSpeechRecognizer) → brain loop | not started |
| **A.3 Real hardware** | serial transport to ESP32 | not started |
| **B Watcher** | classical CV fast loop + small VLM slow loop | not started |
| **C Embodied Gemma** | Gemma 3n E2B unified brain | not started |

Path A.0 is the real accomplishment. Everything downstream now has a
stable socket to plug into.

---

## 8. Directory layout (current)

```
brain/
  schema/
    vocabulary.py                 ← source of truth
    generate.py                   ← regenerates schema + grammar
    behavior.schema.json          ← generated
    behavior.gbnf                 ← generated
  validator.py                    ← parse + clamp + busy-track + stamp
  wire.py                         ← brain schema → firmware wire format
  transport.py                    ← SubprocessBrainstem, StdoutBrainstem
  llm/
    mock.py                       ← rule-based, can emit messy output
    llama_cpp_backend.py          ← GGUF + GBNF, off by default
  main.py                         ← interactive brain loop
  tests/                          ← 45 tests incl. sim integration

mobile/
  README.md                       ← "empty on purpose" — rebuild after A.3

firmware/                         ← existing
  simulation/sim.py               ← the CI integration target
  src/CommandProcessor.h          ← ground truth for wire format
```

---

## 9. What's unresolved / deliberately deferred

- **Android app.** Deleted in this round. Rebuild after Path A.3.
- **Cross-language drift.** Will matter again when Kotlin returns.
- **VLA-style action space.** Current vocab is closed and fixed. If
  locomotion needs finer control (variable turning radius, dynamic stride),
  the firmware needs to expose those params first.
- **Behavior sequencing.** The busy tracker prevents overlap but doesn't
  queue — a fast sequence of commands from the LLM drops all but the
  first. Real choreography needs either explicit sequence commands or a
  queue with bounded depth. Not urgent until we drive the robot harder.
- **Telemetry → prompt.** The sim emits status lines (`positions`,
  `voltage`, `safety`). The brain currently ignores them. Plumbing that
  into the LLM's context is the first step toward closed-loop behavior.
