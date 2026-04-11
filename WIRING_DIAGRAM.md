# PhoneWalker Wiring Diagram

## Board: Waveshare ESP32-S3-Zero
**MAC:** 9c:13:9e:f2:6f:9c

## Pin Connections

### IMU (GY-521/MPU6050)
```
ESP32-S3     GY-521
GPIO 8   --> SDA
GPIO 9   --> SCL  
GND      --> GND
3.3V     --> VCC
```

### Servo Communication (Waveshare Bus Servo Adapter A v1.1)
```
ESP32-S3     Waveshare Adapter
GPIO 17  --> TX
GPIO 18  --> RX
GND      --> GND
```

### Onboard Components
```
GPIO 21  --> WS2812B RGB LED (onboard)
USB-C    --> Programming/Power
```

## Power Supply
- **ESP32-S3**: USB-C (5V) → internal 3.3V
- **GY-521**: 3.3V from ESP32-S3  
- **Servo Adapter**: USB power (independent)
- **Servos**: Power from adapter (6-8.4V)

## Communication Protocols
- **IMU**: I2C (400kHz)
- **Servos**: UART (1000000 baud, half-duplex)
- **RGB LED**: WS2812B protocol (NeoPixel)
- **Debug**: USB Serial (115200 baud)

## Status Indicators (RGB LED)
- 🟡 **Yellow**: Startup
- 🔵 **Blue**: Scanning servos
- 🟢 **Green**: Ready/Servo found
- 🟣 **Magenta**: Walking mode
- 🔴 **Red**: Error