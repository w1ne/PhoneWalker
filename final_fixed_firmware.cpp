// Final Fixed Firmware - Based on Systematic Debug Results
// Implements robust servo communication with findings from tests

#include <Arduino.h>

#define SERVO_SERIAL    Serial1
#define USB_SERIAL      Serial

void setup() {
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🔧 FINAL FIXED PhoneWalker Firmware");
  USB_SERIAL.println("===================================");
  USB_SERIAL.println("Based on systematic debug findings:");
  USB_SERIAL.println("- Servo responds at 1000000 baud");
  USB_SERIAL.println("- Protocol needs adjustment");

  // Use CORRECT baud rate from debug results
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  USB_SERIAL.println("\n🎯 Commands:");
  USB_SERIAL.println("  t = Test communication");
  USB_SERIAL.println("  m = Move servo");
  USB_SERIAL.println("  s = Scan responses");
  USB_SERIAL.println("  d = Dance test");
  USB_SERIAL.println();
}

void sendCommand(uint8_t* packet, int length) {
  // Clear any existing data
  while (SERVO_SERIAL.available()) {
    SERVO_SERIAL.read();
  }

  // Send packet
  SERVO_SERIAL.write(packet, length);

  // Debug output
  USB_SERIAL.printf("SENT: ");
  for (int i = 0; i < length; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();

  // Wait and read response
  delay(100);

  if (SERVO_SERIAL.available() > 0) {
    USB_SERIAL.printf("RECV: ");
    while (SERVO_SERIAL.available()) {
      uint8_t b = SERVO_SERIAL.read();
      USB_SERIAL.printf("%02X ", b);
    }
    USB_SERIAL.println();
  } else {
    USB_SERIAL.println("RECV: NO RESPONSE");
  }
  USB_SERIAL.println();
}

void testCommunication() {
  USB_SERIAL.println("🔍 Testing servo communication...");

  // Test 1: Simple ping
  uint8_t ping[] = {0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB};
  USB_SERIAL.println("1. Ping test:");
  sendCommand(ping, 6);

  delay(500);

  // Test 2: Enable torque
  uint8_t torque[] = {0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD};
  USB_SERIAL.println("2. Enable torque:");
  sendCommand(torque, 9);

  delay(500);

  // Test 3: Simple position command
  uint8_t move[] = {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00, 0xD4};
  USB_SERIAL.println("3. Move command:");
  sendCommand(move, 14);
}

void moveServo() {
  USB_SERIAL.println("🎯 Moving servo with verified working packets...");

  // Use exact packets from working tests
  uint8_t enable_torque[] = {0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD};
  USB_SERIAL.println("Enabling torque:");
  sendCommand(enable_torque, 9);

  delay(1000);

  // Move to different positions with delays
  uint8_t positions[][14] = {
    {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00, 0xD4}, // 2048
    {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0xDC, 0x05, 0xE8, 0x03, 0x00, 0x00, 0xFB}, // 1500
    {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0xC4, 0x09, 0xE8, 0x03, 0x00, 0x00, 0x0F}, // 2500
    {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00, 0xD4}  // 2048
  };

  const char* names[] = {"Center (2048)", "Left (1500)", "Right (2500)", "Center (2048)"};

  for (int i = 0; i < 4; i++) {
    USB_SERIAL.printf("Moving to %s:\n", names[i]);
    sendCommand(positions[i], 14);
    delay(2000);  // Wait for movement
  }

  USB_SERIAL.println("✅ Movement sequence complete");
}

void scanResponses() {
  USB_SERIAL.println("🔍 Scanning servo responses...");

  // Try different servo IDs
  for (int id = 1; id <= 5; id++) {
    USB_SERIAL.printf("Testing servo ID %d:\n", id);

    uint8_t ping[] = {0xFF, 0xFF, (uint8_t)id, 0x02, 0x01, 0};
    ping[5] = (~(ping[2] + ping[3] + ping[4])) & 0xFF; // Calculate checksum

    sendCommand(ping, 6);
    delay(300);
  }
}

void danceTest() {
  USB_SERIAL.println("🕺 Dance test with maximum visibility...");

  // Enable torque first
  uint8_t torque[] = {0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD};
  sendCommand(torque, 9);
  delay(1000);

  // Extreme movements for visibility
  int positions[] = {2048, 1000, 3000, 1500, 2500, 2048};
  const char* names[] = {"Center", "Far Left", "Far Right", "Mid Left", "Mid Right", "Center"};

  for (int i = 0; i < 6; i++) {
    USB_SERIAL.printf("🎭 %s (%d)\n", names[i], positions[i]);

    uint8_t pos_l = positions[i] & 0xFF;
    uint8_t pos_h = (positions[i] >> 8) & 0xFF;

    uint8_t move[] = {0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, pos_l, pos_h, 0xE8, 0x03, 0x00, 0x00, 0};

    // Calculate checksum
    int sum = 0;
    for (int j = 2; j < 13; j++) {
      sum += move[j];
    }
    move[13] = (~sum) & 0xFF;

    sendCommand(move, 14);
    delay(2500);  // Slow movements for visibility
    USB_SERIAL.println("   ⭐ SERVO SHOULD MOVE NOW!");
  }

  USB_SERIAL.println("🎉 Dance complete!");
}

void loop() {
  if (USB_SERIAL.available()) {
    char command = USB_SERIAL.read();

    switch (command) {
      case 't':
        testCommunication();
        break;

      case 'm':
        moveServo();
        break;

      case 's':
        scanResponses();
        break;

      case 'd':
        danceTest();
        break;

      case '\n':
      case '\r':
        break;

      default:
        USB_SERIAL.printf("Unknown command: %c\n", command);
    }
  }

  delay(100);
}