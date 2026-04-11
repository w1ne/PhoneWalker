// Basic Hardware Debug - Check if UART actually works
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("🔧 BASIC HARDWARE DEBUG");
  Serial.println("========================");

  // Initialize UART pins
  Serial1.begin(1000000, SERIAL_8N1, 18, 17);
  delay(1000);

  Serial.println("Testing if UART actually sends data...");
  Serial.println("Commands: s=send test, l=loopback test");
}

void sendTestPattern() {
  Serial.println("\n📡 Sending test pattern to servo...");

  // Send simple repeating pattern
  uint8_t pattern[] = {0xAA, 0x55, 0xAA, 0x55, 0xFF, 0x00, 0xFF, 0x00};

  Serial1.write(pattern, 8);
  Serial.println("Sent: AA 55 AA 55 FF 00 FF 00");

  delay(100);

  // Check if anything comes back
  if (Serial1.available()) {
    Serial.print("Received: ");
    while (Serial1.available()) {
      Serial.printf("%02X ", Serial1.read());
    }
    Serial.println();
  } else {
    Serial.println("NO RESPONSE - Check hardware connection!");
  }
}

void loopbackTest() {
  Serial.println("\n🔄 LOOPBACK TEST");
  Serial.println("Connect TX to RX pin directly to test UART");
  Serial.println("Sending data and checking if we receive it back...");

  // Clear buffer
  while (Serial1.available()) Serial1.read();

  // Send test byte
  Serial1.write(0x42);
  delay(10);

  if (Serial1.available()) {
    uint8_t received = Serial1.read();
    if (received == 0x42) {
      Serial.println("✅ UART WORKING - Loopback successful");
    } else {
      Serial.printf("❌ Wrong data received: %02X\n", received);
    }
  } else {
    Serial.println("❌ UART NOT WORKING - No loopback data");
  }
}

void checkPins() {
  Serial.println("\n📍 PIN CHECK");
  Serial.println("=============");
  Serial.println("ESP32-S3 pins:");
  Serial.println("- TX (pin 17) should connect to Waveshare RX");
  Serial.println("- RX (pin 18) should connect to Waveshare TX");
  Serial.println("- Check continuity with multimeter");
  Serial.println("- Verify Waveshare adapter is powered");
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();

    switch (cmd) {
      case 's':
        sendTestPattern();
        break;

      case 'l':
        loopbackTest();
        break;

      case 'p':
        checkPins();
        break;

      case '\n':
      case '\r':
        break;

      default:
        Serial.printf("Unknown command: %c\n", cmd);
        Serial.println("Use: s=send test, l=loopback, p=pin check");
    }
  }

  delay(100);
}