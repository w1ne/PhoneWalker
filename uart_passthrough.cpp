// UART Passthrough Test - Bypass ESP32 firmware
// This makes ESP32 act as USB-to-UART converter

#include <Arduino.h>

void setup() {
  // USB Serial
  Serial.begin(115200);

  // UART to servos (same settings as firmware)
  Serial1.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17

  Serial.println("🔗 UART Passthrough Mode Active");
  Serial.println("ESP32 → USB ↔ UART ↔ Waveshare ↔ Servos");
  Serial.println("Now test with our working servo scripts!");
}

void loop() {
  // Forward data from USB to UART
  if (Serial.available()) {
    Serial1.write(Serial.read());
  }

  // Forward data from UART to USB
  if (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}