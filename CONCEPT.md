# PhoneWalker
## Concept Document v0.1

---

## What Is It?

A walking platform that gives your phone legs.

You drop your phone into it. Your phone becomes a robot — it walks around, sees where it's going, talks to you, and responds to commands. When you pick the phone back up, it's just a phone again.

The platform does one thing: move. The phone does everything else.

---

## The Core Idea

Every smartphone already contains everything a robot needs — a powerful processor, cameras, microphone, speakers, GPS, WiFi, Bluetooth, and increasingly, on-device AI. The only thing missing is mobility.

PhoneWalker adds mobility. Nothing else.

This means the robot automatically improves every time you upgrade your phone. No new robot needed. No subscription. No proprietary hardware. Just legs.

---

## How It Works

The phone lies flat inside the platform, face up, cradled like a tablet in a case. The platform wraps around it — batteries underneath, legs on the sides, a small mirror beneath the rear camera.

That mirror is the key trick. The rear camera normally points at the ceiling when the phone is flat. A 45-degree mirror redirects its view forward, so the robot sees where it's going. The front camera points upward — useful for recognizing faces of people standing over it. The screen faces up and stays readable. The speaker and microphone face up and work naturally.

The phone connects to the platform over Bluetooth. It sends movement commands — walk forward, turn left, stop — and the platform executes them. The phone stays in control at all times.

---

## What It Can Do

- Walk across a room on its own
- Follow a person using the camera
- Come to you when called
- Look around by turning its body
- Talk and listen through the phone's speaker and mic
- Run any app, assistant, or AI the phone supports
- Charge overnight in a dock, ready to go in the morning

---

## What Makes It Different

Every existing walking robot bundles its own brain — a Raspberry Pi, a custom board, a proprietary chip. That brain is always weaker, more expensive, and more limited than a modern smartphone.

PhoneWalker has no brain of its own. It borrows yours.

This means the platform can be extremely simple and cheap — just servos, a microcontroller, a battery, and a printed frame. The intelligence lives in the phone, where it's already paid for, already connected, and already running the apps you use every day.

No other walking robot works this way.

---

## The Form Factor

```
Top view:

  [ leg ]         [ leg ]
       \           /
        [  PHONE  ]     ← face up, screen visible
       /           \
  [ leg ]         [ leg ]

Side view:

  ___________________
 |                   |   ← phone lying flat
 |___________________|
 |  [mirror] [batt]  |   ← platform body
      |    |    |    
    legs legs legs legs
```

The phone is the widest, flattest, most recognizable part of the robot. It IS the robot. The platform underneath is just infrastructure.

---

## Who Is It For?

**Makers and hobbyists** who want to build something genuinely new, not another Raspberry Pi robot dog clone.

**STEM educators** looking for a platform that teaches robotics, electronics, 3D printing, app development, and AI in a single project — using hardware students already own.

**AI researchers** who want a cheap, open, embodied platform for testing on-device LLMs and computer vision in the real world.

**Anyone curious** about what it feels like when your phone grows legs.

---

## Open Source Philosophy

Everything is open. STL files for printing. Firmware source. App source. Full assembly guide. Anyone can build one from scratch for under $50 in parts, excluding the phone.

The platform is intentionally simple so the community can fork it, improve it, and build on top of it. Different leg designs. Different gaits. Different phone mounts. Different AI behaviors. The concept is the foundation — not the ceiling.

---

## What It Is Not

- Not a toy. Not a pet robot. Not a Roomba.
- Not a finished product trying to replace anything.
- Not dependent on cloud services or subscriptions.
- Not locked to one phone brand or OS.

---

## The One-Line Pitch

> Your phone already has a brain. We just gave it legs.

---

## Open Questions (to be solved in prototyping)

- Best leg geometry for reliable walking with 4 servos
- Universal phone mounting that works across all phone sizes
- Mirror alignment method that doesn't require per-phone calibration
- Minimum viable gait for carpet and uneven surfaces
- How the phone app communicates intent to the platform cleanly
- What behaviors feel useful vs. what feels like a novelty