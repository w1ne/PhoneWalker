// CORRECT Protocol Firmware - Based on ACTUAL working script
// Uses the exact packet format from test_all_servos.sh

#include <Arduino.h>

#define SERVO_SERIAL    Serial1
#define USB_SERIAL      Serial

void setup() {
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🎯 CORRECT Protocol Firmware");
  USB_SERIAL.println("============================");
  USB_SERIAL.println("Using EXACT format from working script");

  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17);
  delay(1000);

  USB_SERIAL.println("Commands: t=test, m=move, d=dance");
}

void sendSTSCommand(int id, int inst, int p1=0, int p2=0, int p3=0, int p4=0, int p5=0, int p6=0, int p7=0, int p8=0) {
  uint8_t packet[16];
  int length = 0;
  uint8_t checksum = 0;

  // Header
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = id;

  if (inst == 1) {
    // PING command - CORRECT format
    packet[3] = 2;  // Length 2
    packet[4] = 1;  // PING instruction
    length = 5;
    checksum = (~(id + 2 + 1)) & 0xFF;

  } else if (inst == 3 && p1 == 40) {
    // Enable torque - CORRECT format
    packet[3] = 4;  // Length 4
    packet[4] = 3;  // Write instruction
    packet[5] = 40; // Torque address
    packet[6] = 0;
    packet[7] = p3; // Enable value
    length = 8;
    checksum = (~(id + 4 + 3 + 40 + 0 + p3)) & 0xFF;

  } else if (inst == 3 && p1 == 42) {
    // Set position - CORRECT format
    packet[3] = 9;  // Length 9
    packet[4] = 3;  // Write instruction
    packet[5] = 42; // Position address
    packet[6] = 0;
    packet[7] = p3; // pos_l
    packet[8] = p4; // pos_h
    packet[9] = p5; // time_l
    packet[10] = p6; // time_h
    packet[11] = p7; // speed_l
    packet[12] = p8; // speed_h
    length = 13;
    checksum = (~(id + 9 + 3 + 42 + 0 + p3 + p4 + p5 + p6 + p7 + p8)) & 0xFF;
  }

  packet[length] = checksum;
  length++;

  // Send packet
  SERVO_SERIAL.write(packet, length);

  // Debug
  USB_SERIAL.printf("SENT (%d bytes): ", length);
  for (int i = 0; i < length; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();

  delay(100);
  if (SERVO_SERIAL.available()) {
    USB_SERIAL.printf("RESPONSE: ");
    while (SERVO_SERIAL.available()) {
      USB_SERIAL.printf("%02X ", SERVO_SERIAL.read());
    }
    USB_SERIAL.println();
  }
  USB_SERIAL.println();
}

void testServo() {
  USB_SERIAL.println("🔍 Testing servo with CORRECT protocol...");

  // Test 1: Ping
  USB_SERIAL.println("1. PING servo 1:");
  sendSTSCommand(1, 1);

  delay(500);

  // Test 2: Enable torque
  USB_SERIAL.println("2. Enable torque:");
  sendSTSCommand(1, 3, 40, 0, 1);  // Enable torque

  delay(1000);

  // Test 3: Move to center
  USB_SERIAL.println("3. Move to center (2048):");
  sendSTSCommand(1, 3, 42, 0, 0, 8, 232, 3, 0, 0);  // pos 2048, time 1000ms

  delay(2000);

  USB_SERIAL.println("✅ Test complete - servo should be stiff and moved");
}

void moveServo() {
  USB_SERIAL.println("🎯 Moving servo with CORRECT protocol...");

  // Enable torque first
  sendSTSCommand(1, 3, 40, 0, 1);
  delay(500);

  // Move sequence
  int positions[][6] = {
    {0, 8, 232, 3, 0, 0},      // 2048 center
    {220, 5, 232, 3, 0, 0},    // 1500 left
    {196, 9, 232, 3, 0, 0},    // 2500 right
    {0, 8, 232, 3, 0, 0}       // 2048 center
  };

  const char* names[] = {"Center", "Left", "Right", "Center"};

  for (int i = 0; i < 4; i++) {
    USB_SERIAL.printf("Moving to %s\n", names[i]);
    sendSTSCommand(1, 3, 42, 0, positions[i][0], positions[i][1],
                   positions[i][2], positions[i][3], positions[i][4], positions[i][5]);
    delay(2000);
  }
}

void danceTest() {
  USB_SERIAL.println("🕺 DANCE with correct protocol!");

  // Enable torque
  sendSTSCommand(1, 3, 40, 0, 1);
  delay(500);

  // Extreme dance moves
  USB_SERIAL.println("Extreme left (1000)");
  sendSTSCommand(1, 3, 42, 0, 232, 3, 232, 3, 0, 0);  // pos 1000
  delay(3000);

  USB_SERIAL.println("Extreme right (3000)");
  sendSTSCommand(1, 3, 42, 0, 184, 11, 232, 3, 0, 0); // pos 3000
  delay(3000);

  USB_SERIAL.println("Back to center");
  sendSTSCommand(1, 3, 42, 0, 0, 8, 232, 3, 0, 0);    // pos 2048
  delay(2000);

  USB_SERIAL.println("🎉 Dance complete!");
}

void loop() {
  if (USB_SERIAL.available()) {
    char cmd = USB_SERIAL.read();

    switch (cmd) {
      case 't':
        testServo();
        break;
      case 'm':
        moveServo();
        break;
      case 'd':
        danceTest();
        break;
      case '\n':
      case '\r':
        break;
      default:
        USB_SERIAL.printf("Unknown: %c\n", cmd);
    }
  }

  delay(100);
}