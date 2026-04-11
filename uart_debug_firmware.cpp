// UART Debug Firmware - Actually READ responses
// Let's see what the servo is actually doing

#include <Arduino.h>

#define SERVO_SERIAL    Serial1
#define USB_SERIAL      Serial

void sendCommand(int servo_id, uint8_t instruction, uint8_t* params, int param_length) {
  uint8_t length = param_length + 2;
  uint8_t packet[64];
  int idx = 0;

  packet[idx++] = 0xFF;
  packet[idx++] = 0xFF;
  packet[idx++] = (uint8_t)servo_id;
  packet[idx++] = length;
  packet[idx++] = instruction;

  for (int i = 0; i < param_length; i++) {
    packet[idx++] = params[i];
  }

  int sum = 0;
  for (int i = 2; i < idx; i++) {
    sum += packet[i];
  }
  packet[idx++] = (~sum) & 0xFF;

  // Clear any existing data
  while (SERVO_SERIAL.available()) {
    SERVO_SERIAL.read();
  }

  // Send command
  SERVO_SERIAL.write(packet, idx);

  // Debug: show what we sent
  USB_SERIAL.printf("SENT: ");
  for (int i = 0; i < idx; i++) {
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
    USB_SERIAL.println("RECV: NO RESPONSE!");
  }
  USB_SERIAL.println();
}

void pingServo(int servo_id) {
  USB_SERIAL.printf("🏓 Pinging servo %d\n", servo_id);
  uint8_t params[] = {};  // No parameters for ping
  sendCommand(servo_id, 0x01, params, 0);
}

void enableTorque(int servo_id) {
  USB_SERIAL.printf("💪 Enabling torque for servo %d\n", servo_id);
  uint8_t params[] = {40, 0, 1};
  sendCommand(servo_id, 0x03, params, 3);
}

void readPosition(int servo_id) {
  USB_SERIAL.printf("📍 Reading position from servo %d\n", servo_id);
  uint8_t params[] = {56, 0, 2, 0};  // Address 56, length 2
  sendCommand(servo_id, 0x02, params, 4);
}

void moveServo(int servo_id, int position) {
  USB_SERIAL.printf("🎯 Moving servo %d to position %d\n", servo_id, position);

  uint8_t pos_l = position & 0xFF;
  uint8_t pos_h = (position >> 8) & 0xFF;

  uint8_t params[] = {42, 0, pos_l, pos_h, 0xE8, 0x03, 0, 0};  // 1000ms move time
  sendCommand(servo_id, 0x03, params, 8);
}

void debugServo(int servo_id) {
  USB_SERIAL.println("🔍 SERVO DEBUG SEQUENCE");
  USB_SERIAL.println("=======================");

  // Step 1: Ping
  pingServo(servo_id);
  delay(500);

  // Step 2: Enable torque
  enableTorque(servo_id);
  delay(500);

  // Step 3: Read position
  readPosition(servo_id);
  delay(500);

  // Step 4: Try to move
  moveServo(servo_id, 1500);
  delay(2000);

  // Step 5: Read position again
  readPosition(servo_id);
  delay(500);

  // Step 6: Move back
  moveServo(servo_id, 2500);
  delay(2000);

  // Step 7: Read final position
  readPosition(servo_id);

  USB_SERIAL.println("🏁 Debug sequence complete");
}

void setup() {
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🔧 UART DEBUG Firmware");
  USB_SERIAL.println("======================");
  USB_SERIAL.println("Let's see what's actually happening on UART");

  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  USB_SERIAL.println("Commands:");
  USB_SERIAL.println("  d = Debug servo 1");
  USB_SERIAL.println("  p = Ping test");
  USB_SERIAL.println("  r = Read position");
  USB_SERIAL.println("  s = Scan for servos");
  USB_SERIAL.println();
}

void loop() {
  if (USB_SERIAL.available()) {
    char command = USB_SERIAL.read();

    switch (command) {
      case 'd':
        debugServo(1);
        break;

      case 'p':
        for (int i = 1; i <= 5; i++) {
          pingServo(i);
          delay(200);
        }
        break;

      case 'r':
        readPosition(1);
        break;

      case 's':
        USB_SERIAL.println("🔍 Scanning for servos...");
        for (int i = 1; i <= 15; i++) {
          USB_SERIAL.printf("Testing servo %d: ", i);
          pingServo(i);
          delay(200);
        }
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