# Getting Started with PhoneWalker

This guide will help you set up and test your PhoneWalker prototype using STS3032 servos.

## Hardware Setup

### Required Components
- 4x Feetech STS3032 smart servos (for legs)
- 1x ESP32 development board (or Arduino Uno)
- 1x Level shifter or direction control circuit (for half-duplex communication)
- Power supply for servos (6-8.4V, capable of 2-3A per servo)
- USB cable for programming and communication

### Wiring Diagram

```
ESP32 Connections:
┌─────────────┐
│    ESP32    │
│             │
│ GPIO16 (TX2)├──┐
│ GPIO17 (RX2)├──┼─── Servo Data Line (half-duplex)
│ GPIO4       ├──┘     (through direction control)
│             │
│ 5V          ├──── Servo VCC (if using 5V servos)
│ GND         ├──── Servo GND + Power Supply GND
│             │
│ USB         ├──── Computer (for commands)
└─────────────┘
```

**Important**: STS3032 servos use half-duplex communication. You need a direction control circuit to switch between TX and RX modes.

## Software Setup

### 1. Install PlatformIO
```bash
# Install PlatformIO CLI
pip install platformio

# Or use PlatformIO IDE (VS Code extension)
```

### 2. Build and Upload Firmware
```bash
cd PhoneWalker/firmware
pio run --target upload
```

### 3. Open Serial Monitor
```bash
pio device monitor --baud 115200
```

## First Test

### 1. Power Up
1. Connect servo power supply (6-8.4V)
2. Connect ESP32 via USB
3. Open serial monitor at 115200 baud

You should see:
```
PhoneWalker Servo Controller v1.0
==================================
Scanning for servos...
Found servos with IDs: 1 2 3 4
Ready for commands:
```

### 2. Basic Servo Test
```
scan                    # Scan for connected servos
ping 1                  # Test communication with servo 1
enable 1                # Enable servo 1 torque
pos 1 2048              # Move servo 1 to center position
get 1                   # Read current position
status                  # Show status of all servos
```

### 3. Walking Test
```
standup                 # Make robot stand up
walk 3                  # Walk forward 3 steps
sitdown                 # Sit back down
```

## Servo ID Configuration

By default, the firmware expects:
- Servo ID 1: Front Left Leg
- Servo ID 2: Front Right Leg  
- Servo ID 3: Back Left Leg
- Servo ID 4: Back Right Leg

If your servos have different IDs, you can either:
1. Change the IDs in firmware (`main.cpp` lines 12-15)
2. Reprogram servo IDs using the manufacturer's tool

## Command Reference

### Basic Commands
- `scan` - Scan for connected servos
- `ping <id>` - Test communication with specific servo
- `pos <id> <position> [time] [speed]` - Set servo position (0-4095)
- `get <id>` - Read current servo position
- `enable <id>` / `disable <id>` - Control servo torque

### Walking Commands
- `standup` - Stand up (enable torque, move to neutral position)
- `sitdown` - Sit down (lower legs, disable torque)
- `walk <steps>` - Walk forward specified number of steps
- `stop` - Stop all movement immediately

### Testing Commands
- `test` - Test each leg servo individually
- `status` - Show comprehensive servo status
- `help` - Show all available commands

## Troubleshooting

### No Servos Found
1. Check power supply connections
2. Verify data line wiring
3. Ensure direction control circuit is working
4. Check servo IDs (default firmware expects IDs 1-4)

### Servo Not Responding
1. Try `ping <id>` to test communication
2. Check servo power (should be 6-8.4V)
3. Verify servo ID matches your configuration
4. Check for loose connections

### Erratic Movement
1. Check power supply capacity (need 2-3A per servo)
2. Verify ground connections
3. Check for electrical interference
4. Adjust movement speeds (slower = more stable)

### Communication Errors
1. Verify baud rate (should be 1,000,000 bps)
2. Check half-duplex direction control
3. Ensure proper level shifting if needed
4. Try lower baud rates for debugging

## Next Steps

Once basic servo control is working:
1. Experiment with different walking gaits
2. Add more servos for additional legs or phone mount
3. Implement Bluetooth communication for phone control
4. Design and 3D print the mechanical frame

## Safety Notes

- Always use appropriate power supply ratings
- Servos can generate significant torque - be careful during testing
- Start with slow movements and low torques
- Ensure emergency stop capability (`stop` command)
- Never leave powered servos unattended