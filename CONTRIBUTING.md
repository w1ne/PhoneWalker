# Contributing to PhoneWalker

Thank you for your interest in contributing to PhoneWalker! This project aims to make walking robots accessible by leveraging the power of smartphones.

## Ways to Contribute

### 🔧 Hardware Contributions
- **Mechanical designs**: Improved leg mechanisms, phone mounts, frame designs
- **Electronics**: Better servo drivers, sensor integration, power management
- **3D models**: STL files for new components or design alternatives
- **Testing**: Real-world testing with different phone types and environments

### 💻 Software Contributions
- **Firmware**: Improved walking gaits, sensor fusion, communication protocols
- **Mobile apps**: iOS/Android apps for robot control
- **Simulation**: Physics simulation for gait development
- **AI integration**: On-device AI for autonomous behaviors

### 📚 Documentation
- **Build guides**: Step-by-step assembly instructions with photos
- **Tutorials**: How-to guides for specific features or modifications
- **Translation**: Documentation in other languages
- **Video guides**: Assembly and operation demonstrations

### 🐛 Bug Reports and Feature Requests
- Report issues with hardware or software
- Suggest new features or improvements
- Share your build experiences and challenges

## Development Setup

### Prerequisites
- **Hardware**: ESP32 or Arduino-compatible board
- **Servos**: STS3032 or compatible smart servos
- **Software**: PlatformIO for firmware development
- **Tools**: 3D printer access (for mechanical components)

### Getting Started
1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/PhoneWalker.git`
3. Follow the [Getting Started Guide](docs/getting-started.md)
4. Set up your development environment

### Building the Firmware
```bash
cd PhoneWalker/firmware
pio run                    # Build firmware
pio run --target upload    # Upload to board
pio device monitor         # Monitor serial output
```

## Contribution Guidelines

### Code Style
- **C++**: Follow standard C++ conventions with clear variable names
- **Comments**: Comment complex algorithms and hardware-specific code
- **Formatting**: Use consistent indentation (2 or 4 spaces)
- **Commits**: Write clear, descriptive commit messages

### Hardware Contributions
- **Documentation**: Include clear documentation for any hardware changes
- **Compatibility**: Ensure designs work with common servo and controller types
- **Safety**: Consider safety implications of mechanical designs
- **Accessibility**: Design for easy assembly with common tools

### Pull Request Process

1. **Create a feature branch**: `git checkout -b feature/your-feature-name`
2. **Make your changes**: Implement your feature or fix
3. **Test thoroughly**: Ensure your changes work as expected
4. **Document changes**: Update relevant documentation
5. **Commit changes**: Use descriptive commit messages
6. **Push to fork**: `git push origin feature/your-feature-name`
7. **Create Pull Request**: Submit PR with clear description

### Pull Request Requirements
- [ ] Code compiles without warnings
- [ ] Changes have been tested on real hardware (when applicable)
- [ ] Documentation updated for any new features
- [ ] Commit messages are clear and descriptive
- [ ] No breaking changes to existing API (unless discussed)

## Project Structure

```
PhoneWalker/
├── firmware/           # Servo control firmware
│   ├── src/           # Main firmware code
│   ├── lib/           # Custom libraries (STS3032)
│   └── platformio.ini # Build configuration
├── hardware/          # Mechanical and electrical designs
│   ├── models/        # 3D printable STL files
│   ├── schematics/    # Wiring and circuit diagrams
│   └── bom.md         # Bill of materials
├── mobile/            # Smartphone apps
│   ├── android/       # Android app
│   └── ios/           # iOS app (future)
├── docs/              # Documentation
├── CONCEPT.md         # Project concept and philosophy
└── README.md          # Main project documentation
```

## Hardware Testing Guidelines

### Safety First
- Always use appropriate power supplies and protection circuits
- Test new mechanical designs with low torque settings first
- Ensure emergency stop capabilities in all firmware
- Document any safety considerations for your changes

### Testing Checklist
- [ ] Servo communication works reliably
- [ ] Mechanical assembly is stable under load
- [ ] Walking gaits are smooth and controlled
- [ ] Power consumption is within expected ranges
- [ ] No overheating of servos or electronics
- [ ] Emergency stop functions work correctly

## Feature Requests and Ideas

We welcome ideas for new features! Some areas of interest:

### Immediate Goals
- [ ] Improved walking stability algorithms
- [ ] Phone app for basic robot control
- [ ] Better servo calibration routines
- [ ] Additional sensor integration (IMU, distance)

### Future Vision
- [ ] Computer vision for autonomous navigation
- [ ] Voice control integration
- [ ] Multi-robot coordination
- [ ] Different locomotion methods (wheels, treads)
- [ ] Advanced AI behaviors using phone's processing power

## Community Guidelines

### Be Respectful
- Welcome newcomers and help them get started
- Provide constructive feedback on contributions
- Respect different approaches and design philosophies
- Acknowledge the work of others

### Share Knowledge
- Document your discoveries and solutions
- Help others troubleshoot their builds
- Share interesting modifications or improvements
- Contribute to discussions in issues and pull requests

### Open Source Spirit
- Keep the project accessible to makers and hobbyists
- Avoid proprietary dependencies when possible
- Document everything clearly for future contributors
- Consider the global maker community in design decisions

## Questions?

- **Issues**: Open a GitHub issue for bug reports or feature requests
- **Discussions**: Use GitHub Discussions for general questions
- **Documentation**: Check the [Getting Started Guide](docs/getting-started.md)
- **Email**: Contact project maintainers for sensitive issues

Thank you for helping make PhoneWalker better! Every contribution, no matter how small, helps advance the goal of making robotics more accessible to everyone.

## Recognition

Contributors will be recognized in:
- Project README acknowledgments
- Release notes for significant contributions
- Special recognition for innovative hardware designs
- Community showcase for exceptional builds