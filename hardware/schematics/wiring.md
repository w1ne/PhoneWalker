# PhoneWalker Wiring Schematic

## Main Connections

### ESP32 to Servo Communication

```
ESP32                    Direction Control               Servo Bus
┌─────────────┐         ┌─────────────────┐            ┌─────────────┐
│             │         │   74HC126       │            │   STS3032   │
│ GPIO16 (TX2)├─────────┤1A            1Y├────────────┤Data         │
│ GPIO17 (RX2)├─────────┤2A            2Y├────────────┤Data         │
│ GPIO4       ├─────────┤1OE,2OE          │            │             │
│             │         │                 │            │ VCC ────────┼─── +7.4V
│ VIN (5V)    ├─────────┤VCC              │            │ GND ────────┼─── GND
│ GND         ├─────────┤GND              │            │             │
└─────────────┘         └─────────────────┘            └─────────────┘
```

### Power Distribution

```
Battery Pack (7.4V LiPo)
         │
         ├─── Main Switch ─── Fuse (5A) ─── Power LED
         │                                      │
         ├──────────────────────────────────────┴─── Servo VCC (All Servos)
         │                                      
         └─── Buck Converter (7.4V → 5V) ─── ESP32 VIN
                                             
All GND connections tied together
```

## Pin Assignments

### ESP32 Pins
| Pin | Function | Connection |
|-----|----------|------------|
| GPIO16 | UART2 TX | Direction control input |
| GPIO17 | UART2 RX | Direction control input |
| GPIO4 | Direction Control | Enable signal for 74HC126 |
| VIN | 5V Power | From buck converter |
| GND | Ground | Common ground |
| USB | Programming/Debug | Computer connection |

### Servo Connections (All Servos)
| Wire | Function | Connection |
|------|----------|------------|
| Red | Power (VCC) | 7.4V from battery |
| Black/Brown | Ground (GND) | Common ground |
| Yellow/White | Data | Half-duplex bus |

## Direction Control Circuit

The STS3032 servos use half-duplex communication - they share one wire for both sending and receiving data. We need a direction control circuit to manage this.

### Using 74HC126 Quad Buffer

```
         ESP32                    74HC126                   Servo Bus
    ┌──────────┐              ┌────────────┐               
TX2 │ GPIO16   ├──────────────┤1A      1Y├────────────┐    
RX2 │ GPIO17   ├──────────────┤2A      2Y├──────────┐ │    
    │ GPIO4    ├────┬─────────┤1OE     3Y├──────────┼─┼──── Data Line
    └──────────┘    │      ┌──┤2OE     4Y├──────────┘ │    
                    │      │  └────────────┘           │    
                    │      │                           │    
                    └──────┴───────────────────────────┘    
```

**Logic:**
- When GPIO4 is HIGH: TX enabled, ESP32 transmits to servos
- When GPIO4 is LOW: RX enabled, servos can send data to ESP32

## Servo Bus Topology

### Daisy Chain Connection

```
ESP32 ──── Direction Control ──── Servo 1 ──── Servo 2 ──── Servo 3 ──── Servo 4
                                    │           │           │           │
                                   ID:1        ID:2        ID:3        ID:4
                                    │           │           │           │
Power Bus: 7.4V ───────────────────┴───────────┴───────────┴───────────┘
Ground Bus: GND ───────────────────┬───────────┬───────────┬───────────┐
                                    │           │           │           │
```

### Servo ID Assignment
| Servo Position | ID | Function |
|----------------|----| ---------|
| Front Left | 1 | Primary leg |
| Front Right | 2 | Primary leg |
| Back Left | 3 | Primary leg |
| Back Right | 4 | Primary leg |
| Extra Servos | 5-15 | Future expansion |

## Power Specifications

### Battery Requirements
- **Voltage**: 7.4V (2S LiPo)
- **Capacity**: 3000mAh minimum (5000mAh recommended)
- **C-Rating**: 20C minimum (for 3000mAh = 60A burst capability)
- **Connector**: XT60 or similar high-current connector

### Current Draw Analysis
```
Component          Peak Current    Typical Current
─────────────────────────────────────────────────
STS3032 (each)           2.5A             0.5A
4x Servos total         10.0A             2.0A
ESP32                    0.2A             0.1A
Direction Control        0.05A            0.05A
─────────────────────────────────────────────────
Total System           ~10.3A            ~2.2A
```

### Protection
- **Main Fuse**: 5A slow-blow
- **Buck Converter**: Built-in overcurrent protection
- **Battery**: Use LiPo with built-in protection circuit

## Assembly Notes

### Critical Connections
1. **Power polarity**: Double-check before connecting battery
2. **Servo data**: Must be half-duplex with proper direction control
3. **Ground loops**: Ensure single-point grounding
4. **Wire gauge**: Use 16-18 AWG for servo power, 22-24 AWG for signals

### Testing Sequence
1. Connect ESP32 to computer (no servo power)
2. Upload firmware and test serial communication
3. Connect direction control circuit (no servo power)
4. Test direction control with oscilloscope/logic analyzer
5. Connect single servo with power
6. Test basic servo communication
7. Add remaining servos one by one

### Safety Checklist
- [ ] Fuse installed in power line
- [ ] Power switch easily accessible
- [ ] No short circuits (multimeter continuity test)
- [ ] Proper wire gauge for current capacity
- [ ] Secure connections (no loose wires)
- [ ] Battery properly secured and protected

## Troubleshooting

### Common Issues
| Problem | Possible Cause | Solution |
|---------|----------------|----------|
| No servo response | Direction control not working | Check 74HC126 connections |
| Intermittent communication | Loose connections | Secure all wiring |
| Servo overheating | Insufficient power supply | Upgrade battery/wiring |
| ESP32 reset | Power supply dropout | Add capacitors, check connections |

### Debug Tools
- Multimeter for voltage/continuity testing
- Oscilloscope for signal timing analysis
- Logic analyzer for protocol debugging
- Thermal camera/thermometer for heat issues