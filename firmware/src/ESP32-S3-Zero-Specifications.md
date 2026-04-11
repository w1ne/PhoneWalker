# Waveshare ESP32-S3-Zero Board Specifications

## Board Identification
- **Model**: ESP32-S3-Zero
- **Manufacturer**: Waveshare
- **Target MAC Address**: 9c:13:9e:f2:6f:9c
- **Chip**: ESP32-S3FH4R2 (ESP32-S3 series)
- **Package**: QFN56 (7×7 mm)

## Main Specifications
- **CPU**: Xtensa 32-bit LX7 dual-core microprocessor
- **Wi-Fi**: 2.4 GHz (IEEE 802.11b/g/n) 
- **Bluetooth**: Bluetooth 5 (LE)
- **Flash/PSRAM**: Optional 1.8V or 3.3V in chip package
- **GPIO Pins**: 45 GPIOs total
- **Operating Voltage**: 3.3V
- **USB Interface**: USB Type-C for programming and power

## LED Configuration

### Onboard LED Specifications
- **Type**: WS2812B RGB LED
- **Part Number**: XL-0807RGBC-WS2812B (Xinglight)
- **GPIO Pin**: GPIO21
- **Package**: 0807 (2.0 × 1.8 × 0.8 mm)
- **Control Method**: Single-wire digital control
- **Voltage**: 3.3V
- **Current**: 1.75mA ~ 19mA per LED (adjustable with 16 current gain levels)
- **PWM Frequency**: Up to 4kHz
- **Protocol**: WS2812 protocol (unipolar return to zero code)

### LED Control Details
- **Data Pin**: GPIO21 (DIN of WS2812B)
- **Control Library**: Adafruit NeoPixel or FastLED
- **Color Format**: 24-bit RGB (8 bits per color channel)
- **Default State**: Off when powered on
- **Refresh Rate**: Single line transmission, synchronous output

## Pin Configuration (Key Pins)

### LED Pin
- **GPIO21**: WS2812B RGB LED (DIN)

### Programming Pins
- **GPIO0**: BOOT button (for programming mode)
- **RESET**: Reset button
- **USB_D+/USB_D-**: USB Type-C data lines for programming

### Power Pins
- **VIN**: Input voltage via Type-C
- **3V3**: 3.3V regulated output
- **GND**: Ground

## Programming Information

### Arduino IDE Setup
1. Install ESP32 board package
2. Select "ESP32S3 Dev Module" as board
3. Set USB CDC on Boot: "Enabled"
4. Set PSRAM: "Disabled" (or as needed)
5. Set Flash Size: As per your module

### Programming Mode
- Press and hold BOOT button (GPIO0)
- Press and release RESET button
- Release BOOT button
- Board is now in download mode

## Code Libraries Required

### For LED Control
```cpp
#include <Adafruit_NeoPixel.h>
// or
#include <FastLED.h>
```

### Basic LED Setup
```cpp
#define LED_PIN 21
#define LED_COUNT 1
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);
```

## Official Documentation Links

### Datasheets (Downloaded)
- `esp32-s3-zero-schematic.pdf` - Board schematic
- `ws2812-led-spec.pdf` - WS2812B LED specifications  
- `esp32-s3-datasheet.pdf` - ESP32-S3 chip datasheet

### Online Resources
- **Waveshare Wiki**: https://www.waveshare.com/wiki/ESP32-S3-Zero
- **Schematic PDF**: https://files.waveshare.com/wiki/ESP32-S3-Zero/ESP32-S3-Zero-Sch.pdf
- **WS2812 Spec**: https://files.waveshare.com/wiki/ESP32-S3-Zero/XL-0807RGBC-WS2812B.pdf
- **ESP32-S3 Datasheet**: https://documentation.espressif.com/esp32-s3_datasheet_en.pdf

## Working Code Example
See `ESP32-S3-Zero-LED-Example.ino` for a complete Arduino sketch demonstrating:
- Basic LED initialization
- Color wipe effects
- Rainbow cycling
- Breathing effects
- All standard WS2812 control functions

## Notes
- The board uses a single WS2812B LED, not an LED strip
- GPIO21 is hardwired to the LED's DIN pin
- LED requires WS2812 protocol timing, not simple digitalWrite
- Use NeoPixel or FastLED library for proper control
- Default brightness should be limited to prevent excessive power draw