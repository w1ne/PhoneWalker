# PhoneWalker Bill of Materials

## Electronics Components

### Required Components

| Component | Quantity | Description | Estimated Cost | Notes |
|-----------|----------|-------------|---------------|-------|
| Feetech STS3032 Servo | 4 | Smart serial servo, 35kg-cm torque | $25 each | Main leg actuators |
| ESP32 Development Board | 1 | Microcontroller with WiFi/Bluetooth | $10 | ESP32-WROOM-32 recommended |
| 74HC126 Quad Buffer | 1 | For half-duplex direction control | $1 | Alternative: SN74LVC1G125 |
| LiPo Battery | 1 | 7.4V 2S, 3000mAh minimum | $25 | Powers servos |
| LiPo Charger | 1 | Balance charger for 2S LiPo | $15 | Safety essential |
| Voltage Regulator | 1 | 7.4V to 5V, 3A capacity | $5 | LM2596 buck converter |
| Jumper Wires | 1 set | Various lengths | $5 | For prototyping |
| Breadboard/Perfboard | 1 | For connections | $5 | Temporary or permanent mounting |

### Optional Components

| Component | Quantity | Description | Estimated Cost | Notes |
|-----------|----------|-------------|---------------|-------|
| Additional STS3032 | 11 | Extra servos for experimentation | $25 each | You mentioned having 15 total |
| Power Switch | 1 | Main power on/off | $2 | Safety feature |
| Power LED | 1 | Power indicator | $1 | Visual feedback |
| Capacitors | 2-4 | 1000µF electrolytic, power filtering | $2 each | Reduces power spikes |
| Fuses | 2 | 5A automotive fuses | $1 each | Protection |

## Mechanical Components (3D Printed/Fabricated)

### Frame Structure

| Component | Quantity | Description | Material | Notes |
|-----------|----------|-------------|----------|-------|
| Main Body Frame | 1 | Houses phone and electronics | PLA/PETG | To be designed |
| Leg Brackets | 4 | Mount servos to frame | PLA/PETG | Servo horn compatible |
| Phone Mount | 1 | Universal phone holder | TPU/PLA | Adjustable design |
| Servo Horns | 4 | Connect legs to servos | Aluminum/Plastic | Usually included with servos |
| Mirror Mount | 1 | 45° camera redirect | PLA | For camera redirection |

### Hardware

| Component | Quantity | Description | Size | Notes |
|-----------|----------|-------------|------|-------|
| Machine Screws | 16 | Servo mounting screws | M3x12mm | Usually included |
| Machine Screws | 8 | Frame assembly | M3x8mm | General assembly |
| Nuts | 8 | Frame assembly | M3 | Hex or nylon lock |
| Mirror | 1 | Camera redirection | 25x25mm | 45° first surface mirror |

## Tools Required

| Tool | Purpose | Notes |
|------|---------|-------|
| 3D Printer | Frame fabrication | 200x200mm build volume minimum |
| Soldering Iron | Electronics assembly | Temperature controlled preferred |
| Wire Strippers | Cable preparation | Essential for connections |
| Multimeter | Testing/debugging | Voltage and continuity testing |
| Screwdriver Set | Assembly | Phillips and hex keys |
| Heat Shrink Tubing | Wire insulation | Various sizes |

## Cost Breakdown

### Minimum Viable Prototype (4 servos)
- Servos (4x): $100
- ESP32: $10
- Electronics: $15
- Battery/Charger: $40
- Misc hardware: $20
- **Total: ~$185**

### Full Development Kit (15 servos + extras)
- Servos (15x): $375
- ESP32: $10
- Electronics: $25
- Battery/Power: $60
- 3D printing materials: $30
- Tools/misc: $50
- **Total: ~$550**

## Supplier Recommendations

### Electronics
- **Servos**: Feetech official distributors, RobotShop
- **ESP32**: SparkFun, Adafruit, AliExpress
- **General**: Digi-Key, Mouser, Amazon

### 3D Printing
- **Filament**: Hatchbox, SUNLU, Overture
- **Services**: Shapeways, Craftcloud (if no printer)

### Batteries
- **LiPo**: HobbyKing, Amazon (check reviews)
- **Safety**: Always use balance chargers and fire-safe storage

## Power Calculations

### Current Draw
- Each STS3032: 2.5A peak, 0.5A idle
- ESP32: 0.2A active, 0.01A deep sleep
- **Total (4 servos)**: ~10.5A peak, ~2.2A typical

### Battery Life
- 3000mAh battery @ 2.2A average: ~1.3 hours
- 5000mAh battery recommended for longer operation

### Safety Notes
- **LiPo batteries can be dangerous** - follow charging safety protocols
- Use appropriate fuses and protection circuits
- Never leave charging batteries unattended
- Store in fireproof containers

## Future Upgrades

### Possible Additions
- IMU sensor for balance feedback
- Distance sensors for obstacle avoidance
- Better motor drivers for efficiency
- Wireless charging for phone
- RGB LEDs for visual feedback