# Mobile app

Empty on purpose. The Kotlin scaffolding that lived here was torn out after a
self-review — it claimed to ship an app but was a text-box wrapping a
placeholder LLM, stale against the real firmware vocabulary, and never
compiled against a MediaPipe dependency or a phone.

The right time to start the Android app is after:

1. The Python brain (`../brain/`) drives the PyBullet simulator reliably
   via the real firmware wire protocol. (Done — see
   `brain/tests/test_sim_integration.py`.)
2. The Python brain drives a real ESP32 over serial/USB. (TODO.)
3. A chosen on-device LLM (start with Gemma 3 1B via MediaPipe LLM
   Inference) has been benchmarked on a target handset.

At that point the Kotlin port is a 1:1 translation of:

* `brain/schema/vocabulary.py` → `Vocabulary.kt`
* `brain/validator.py` → `Validator.kt`
* `brain/wire.py` → `Wire.kt`
* `brain/transport.py` (serial/ble variant) → `Transport.kt`

Keep the validator/wire unit tests mirrored. Do not build Android UI
before the backend/brain loop is proven — that was the mistake last time.
