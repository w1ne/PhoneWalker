# PhoneWalker

**Your phone already has a brain. We just gave it legs.**

PhoneWalker is an open-source walking platform that turns any smartphone into a mobile robot. Drop your phone in, and it becomes a walking, talking, seeing robot. Pick it up, and it's just a phone again.

## 🚀 Quick Start

1. **Hardware**: Build the platform using our 3D-printable parts and servo kit
2. **Firmware**: Flash the control firmware to your microcontroller
3. **App**: Install the companion app on your phone
4. **Walk**: Your phone now has legs!

## 📁 Repository Structure

```
├── firmware/           # Platform control firmware
│   ├── src/           # Source code
│   ├── lib/           # Libraries (servo control, comms)
│   └── platformio.ini # PlatformIO configuration
├── hardware/          # 3D models and electronics
│   ├── models/        # STL files for 3D printing
│   ├── schematics/    # Circuit diagrams
│   └── bom.md         # Bill of materials
├── mobile/            # Smartphone apps
│   ├── android/       # Android app
│   └── ios/           # iOS app (future)
├── docs/              # Documentation and guides
│   ├── assembly.md    # Build instructions
│   ├── api.md         # Communication protocol
│   └── troubleshooting.md
├── CONCEPT.md         # Detailed concept document
└── LICENSE
```

## 🔧 Current Status: Prototype Phase

We're currently building the first working prototype. This includes:

- [x] Concept and specification
- [ ] Servo control firmware (STS3032 support)
- [ ] Basic walking gait implementation
- [ ] Bluetooth communication protocol
- [ ] Phone app MVP
- [ ] 3D-printable frame design

## 🤖 Hardware Requirements

**Servos**: 4x Feetech STS3032 smart servos (or compatible)
**Controller**: ESP32 or Arduino-compatible microcontroller
**Communication**: Bluetooth module (built into ESP32)
**Power**: LiPo battery pack
**Frame**: 3D-printed platform body

## 📖 Documentation

- [**Concept Document**](CONCEPT.md) - The full vision and philosophy
- [**Assembly Guide**](docs/assembly.md) - How to build your own (coming soon)
- [**API Documentation**](docs/api.md) - Phone-to-platform communication (coming soon)

## 🤝 Contributing

This is an open-source project. We welcome:
- Hardware improvements and alternative designs
- Firmware contributions and optimizations  
- Mobile app development
- Documentation and tutorials
- Testing and bug reports

See our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

**Join the movement**: Help us make every smartphone a potential robot.