"""Source of truth for the PhoneWalker brain→brainstem behavior vocabulary.

Aligned to the firmware in ``firmware/src/MotionController.h`` and
``firmware/src/CommandProcessor.h``. Do not add a behavior here unless the
firmware actually implements it — the simulator is the ground-truth check
(see ``brain/tests/test_sim_integration.py``).

When you change this file, run ``python3 -m brain.schema.generate`` to
refresh ``behavior.schema.json`` and ``behavior.gbnf``.
"""

from __future__ import annotations

SCHEMA_VERSION = 1

# Named poses defined in firmware/src/MotionController.h:POSE_TABLE.
POSES = (
    "neutral",
    "bow_front",
    "lean_left",
    "lean_right",
    "stretch_diagonal1",
    "stretch_diagonal2",
    "twist_front_left",
    "twist_front_right",
)

# Gait primitives implemented by firmware/src/GaitController.h and handled by
# CommandProcessor (``walk``, ``jump``). ``stop`` returns to neutral;
# ``estop`` cuts torque.
GAIT = ("walk", "jump")
LIFECYCLE = ("stop", "estop")

BEHAVIORS = POSES + GAIT + LIFECYCLE

TRANSITIONS = ("instant", "linear", "smooth", "bounce")

# Parameter ranges: (lo, hi, default). Types inferred from the default.
PARAM_RANGES = {
    # speed for ``pose`` is a servo unit (100-3400 on ST servos); default 1500.
    "speed": (100, 3400, 1500),
    # duration_ms is a phone-side concept for choreography timing; the ESP32
    # receives `d` = servo speed (mapped from duration upstream if needed).
    "duration_ms": (100, 5000, 1000),
    "hold_ms": (0, 5000, 0),
    # Gait parameters, matched to firmware defaults.
    "stride": (50, 400, 150),
    "step_ms": (100, 1000, 400),
}

# Text-layer emergency detection. NOT a full safety system — the real
# watchdog lives on the ESP32 (see firmware/src/SafetySystem.h). This
# just catches obvious verbal bail-outs on the phone before an LLM round-trip.
EMERGENCY_TRANSCRIPTS = (
    "estop", "emergency", "freeze", "halt", "abort", "kill", "panic",
)

# Durations used by the "behavior-in-progress" tracker in the validator when
# the model doesn't supply duration_ms explicitly. Values in milliseconds.
DEFAULT_DURATION_MS = {
    "neutral":           600,
    "bow_front":         900,
    "lean_left":         700,
    "lean_right":        700,
    "stretch_diagonal1": 900,
    "stretch_diagonal2": 900,
    "twist_front_left":  700,
    "twist_front_right": 700,
    "walk":              0,     # continuous until stopped
    "jump":              1200,
    "stop":              400,
    "estop":             0,     # instantaneous, preempts everything
}
