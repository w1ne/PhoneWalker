// PhoneWalker Dancing Firmware - CORRECTED PROTOCOL
// Uses verified packet building from comparison test

#include <Arduino.h>

#define SERVO_SERIAL    Serial1
#define USB_SERIAL      Serial

struct ServoMove {
  int position;
  int time_ms;
  const char* name;
};

// Dance routines
ServoMove test_dance[] = {
  {2048, 1500, "Center"},
  {1500, 1500, "Left"},
  {2500, 1500, "Right"},
  {2048, 1500, "Center"},
  {0, 0, "END"}
};

// CORRECTED packet building function (from comparison test)
void sendServoCommand(int servo_id, uint8_t instruction, uint8_t* params, int param_length) {
  uint8_t length = param_length + 2; // instruction + checksum

  // Build packet array
  uint8_t packet[64];
  int idx = 0;

  packet[idx++] = 0xFF;
  packet[idx++] = 0xFF;
  packet[idx++] = (uint8_t)servo_id;
  packet[idx++] = length;
  packet[idx++] = instruction;

  // Add parameters
  for (int i = 0; i < param_length; i++) {
    packet[idx++] = params[i];
  }

  // Calculate checksum (from ID onwards, excluding header)
  int sum = 0;
  for (int i = 2; i < idx; i++) {
    sum += packet[i];
  }
  packet[idx++] = (~sum) & 0xFF;

  // Send to servo
  SERVO_SERIAL.write(packet, idx);

  // Debug output to verify packets
  USB_SERIAL.printf("Sent %d bytes: ", idx);
  for (int i = 0; i < idx; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();
}

void enableTorque(int servo_id) {
  USB_SERIAL.printf("💪 Enabling torque for servo %d\n", servo_id);

  // Exact parameters from working Python script
  uint8_t params[] = {40, 0, 1};  // Address 40, value 1
  sendServoCommand(servo_id, 0x03, params, 3);
  delay(500);  // Longer delay for torque enable
}

void moveServo(int servo_id, int position, int time_ms) {
  USB_SERIAL.printf("🎯 Moving servo %d to position %d (%dms)\n", servo_id, position, time_ms);

  // Convert position and time to bytes (little endian)
  uint8_t pos_l = position & 0xFF;
  uint8_t pos_h = (position >> 8) & 0xFF;
  uint8_t time_l = time_ms & 0xFF;
  uint8_t time_h = (time_ms >> 8) & 0xFF;

  // Address 42 (Goal Position), exact format from working script
  uint8_t params[] = {42, 0, pos_l, pos_h, time_l, time_h, 0, 0};
  sendServoCommand(servo_id, 0x03, params, 8);
}

void performDance(ServoMove* dance, const char* dance_name, int servo_id) {
  USB_SERIAL.printf("\n🕺 Starting %s Dance! 🕺\n", dance_name);
  USB_SERIAL.println("==========================================");

  // Enable torque first (CRITICAL!)
  enableTorque(servo_id);

  // Execute dance moves
  int move_count = 0;
  while (dance[move_count].time_ms != 0) {
    ServoMove* move = &dance[move_count];

    USB_SERIAL.printf("\n🎭 Move %d: %s\n", move_count + 1, move->name);
    moveServo(servo_id, move->position, move->time_ms);

    // Wait for movement completion + extra time
    delay(move->time_ms + 1000);
    USB_SERIAL.println("   ⏰ Move should be complete");

    move_count++;
  }

  USB_SERIAL.printf("\n🎊 %s Dance Complete! 🎊\n\n", dance_name);
}

void testSingleMove(int servo_id) {
  USB_SERIAL.println("🔧 SINGLE MOVE TEST");
  USB_SERIAL.println("===================");

  enableTorque(servo_id);

  USB_SERIAL.println("📍 Moving to EXTREME positions for visibility:");

  // Very obvious movements
  int positions[] = {2048, 1000, 3000, 2048};
  const char* names[] = {"Center", "Far Left", "Far Right", "Center"};

  for (int i = 0; i < 4; i++) {
    USB_SERIAL.printf("\n   %s (%d)\n", names[i], positions[i]);
    moveServo(servo_id, positions[i], 2000);  // Slow movement
    delay(3000);  // Long wait
    USB_SERIAL.println("   ⭐ Should see movement NOW!");
  }

  USB_SERIAL.println("✅ Single move test complete");
}

void setup() {
  // Initialize USB serial
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🎭 PhoneWalker CORRECTED Dancing Firmware 🎭");
  USB_SERIAL.println("=============================================");
  USB_SERIAL.println("Using verified packet protocol from comparison test");

  // Initialize servo serial with CORRECT pins (from our working tests)
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  USB_SERIAL.println("🎵 Ready! Commands:");
  USB_SERIAL.println("  t = Test single moves (very obvious)");
  USB_SERIAL.println("  d = Test dance");
  USB_SERIAL.println("  e = Enable torque only");
  USB_SERIAL.println();
}

void loop() {
  if (USB_SERIAL.available()) {
    char command = USB_SERIAL.read();
    int servo_id = 1;

    switch (command) {
      case 't':
        testSingleMove(servo_id);
        break;

      case 'd':
        performDance(test_dance, "Test", servo_id);
        break;

      case 'e':
        USB_SERIAL.println("💪 Torque enable test");
        enableTorque(servo_id);
        USB_SERIAL.println("✅ Torque enabled");
        break;

      case '\n':
      case '\r':
        // Ignore newlines
        break;

      default:
        USB_SERIAL.printf("❓ Unknown command '%c'. Use t/d/e\n", command);
    }
  }

  delay(100);
}