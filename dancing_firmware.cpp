// PhoneWalker Dancing Firmware
// Autonomous servo dancing with position feedback

#include <Arduino.h>

#define SERVO_SERIAL    Serial1
#define USB_SERIAL      Serial

struct ServoMove {
  int position;
  int time_ms;
  const char* name;
};

// Dance routines
ServoMove wave_dance[] = {
  {2048, 500, "Center"},
  {1500, 400, "Left"},
  {2500, 400, "Right"},
  {1800, 300, "Mid-Left"},
  {2300, 300, "Mid-Right"},
  {2048, 500, "Center"},
  {0, 0, "END"}
};

ServoMove shake_dance[] = {
  {2048, 200, "Start"},
  {1700, 150, "Shake-L1"},
  {2400, 150, "Shake-R1"},
  {1700, 100, "Shake-L2"},
  {2400, 100, "Shake-R2"},
  {1700, 100, "Shake-L3"},
  {2400, 100, "Shake-R3"},
  {2048, 300, "Stop"},
  {0, 0, "END"}
};

ServoMove robot_dance[] = {
  {2048, 300, "Ready"},
  {1500, 250, "Step1"},
  {1500, 100, "Hold1"},
  {2500, 250, "Step2"},
  {2500, 100, "Hold2"},
  {1800, 200, "Step3"},
  {2300, 200, "Step4"},
  {2048, 400, "Finish"},
  {0, 0, "END"}
};

void sendServoCommand(int servo_id, int position, int time_ms) {
  uint8_t pos_l = position & 0xFF;
  uint8_t pos_h = (position >> 8) & 0xFF;
  uint8_t time_l = time_ms & 0xFF;
  uint8_t time_h = (time_ms >> 8) & 0xFF;

  // Build SCServo packet
  uint8_t packet[] = {
    0xFF, 0xFF,           // Header
    (uint8_t)servo_id,    // ID
    10,                   // Length
    0x03,                 // Write instruction
    42, 0,                // Address (Goal Position)
    pos_l, pos_h,         // Position
    time_l, time_h,       // Time
    0, 0,                 // Speed (0 = max)
    0                     // Checksum placeholder
  };

  // Calculate checksum
  int sum = 0;
  for (int i = 2; i < 12; i++) {
    sum += packet[i];
  }
  packet[12] = (~sum) & 0xFF;

  // Send packet
  SERVO_SERIAL.write(packet, 13);

  USB_SERIAL.printf("🎯 Servo %d → %d (%dms)\n", servo_id, position, time_ms);
}

int readServoPosition(int servo_id) {
  // Send read position command
  uint8_t packet[] = {
    0xFF, 0xFF,           // Header
    (uint8_t)servo_id,    // ID
    6,                    // Length
    0x02,                 // Read instruction
    56, 0,                // Address (Present Position)
    2, 0,                 // Length to read
    0                     // Checksum placeholder
  };

  // Calculate checksum
  int sum = 0;
  for (int i = 2; i < 8; i++) {
    sum += packet[i];
  }
  packet[8] = (~sum) & 0xFF;

  // Send packet
  SERVO_SERIAL.write(packet, 9);
  delay(50);

  // Read response
  if (SERVO_SERIAL.available() >= 7) {
    uint8_t response[10];
    int bytes_read = SERVO_SERIAL.readBytes(response, 10);

    if (bytes_read >= 7 && response[0] == 0xFF && response[1] == 0xFF) {
      int position = response[5] | (response[6] << 8);
      return position;
    }
  }
  return -1;
}

void enableTorque(int servo_id) {
  uint8_t packet[] = {
    0xFF, 0xFF,           // Header
    (uint8_t)servo_id,    // ID
    5,                    // Length
    0x03,                 // Write instruction
    40, 0,                // Address (Torque Enable)
    1,                    // Enable
    0                     // Checksum placeholder
  };

  // Calculate checksum
  int sum = 0;
  for (int i = 2; i < 7; i++) {
    sum += packet[i];
  }
  packet[7] = (~sum) & 0xFF;

  SERVO_SERIAL.write(packet, 8);
  USB_SERIAL.printf("💪 Torque enabled for servo %d\n", servo_id);
}

void performDance(ServoMove* dance, const char* dance_name, int servo_id) {
  USB_SERIAL.printf("\n🕺 Starting %s Dance! 🕺\n", dance_name);
  USB_SERIAL.println("=================================");

  // Enable torque
  enableTorque(servo_id);
  delay(200);

  // Execute dance moves
  int move_count = 0;
  while (dance[move_count].time_ms != 0) {
    ServoMove* move = &dance[move_count];

    // Read current position
    int current_pos = readServoPosition(servo_id);
    USB_SERIAL.printf("📊 Current: %d\n", current_pos);

    // Send move command
    USB_SERIAL.printf("🎭 Move %d: %s\n", move_count + 1, move->name);
    sendServoCommand(servo_id, move->position, move->time_ms);

    // Wait for completion
    delay(move->time_ms + 200);

    // Read final position for feedback
    int final_pos = readServoPosition(servo_id);
    int error = abs(final_pos - move->position);
    const char* status = (error < 50) ? "✅" : "⚠️";

    USB_SERIAL.printf("📍 Final: %d %s (target: %d, error: %d)\n",
                     final_pos, status, move->position, error);
    USB_SERIAL.println();

    move_count++;
    delay(100);
  }

  USB_SERIAL.printf("🎊 %s Dance Complete! 🎊\n\n", dance_name);
}

void setup() {
  // Initialize USB serial
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🎭 PhoneWalker Dancing Firmware 🎭");
  USB_SERIAL.println("===================================");
  USB_SERIAL.println("Autonomous servo dancing with position feedback");

  // Initialize servo communication with fixed pins
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  USB_SERIAL.println("🎵 Ready to dance! Commands:");
  USB_SERIAL.println("  w = Wave dance");
  USB_SERIAL.println("  s = Shake dance");
  USB_SERIAL.println("  r = Robot dance");
  USB_SERIAL.println("  p = Party mode (all dances)");
  USB_SERIAL.println();
}

void loop() {
  if (USB_SERIAL.available()) {
    char command = USB_SERIAL.read();
    int servo_id = 1; // Primary servo

    switch (command) {
      case 'w':
        performDance(wave_dance, "Wave", servo_id);
        break;

      case 's':
        performDance(shake_dance, "Shake", servo_id);
        break;

      case 'r':
        performDance(robot_dance, "Robot", servo_id);
        break;

      case 'p':
        USB_SERIAL.println("🎉 PARTY MODE! 🎉");
        performDance(wave_dance, "Wave", servo_id);
        delay(500);
        performDance(shake_dance, "Shake", servo_id);
        delay(500);
        performDance(robot_dance, "Robot", servo_id);
        USB_SERIAL.println("🎊 Party complete! 🎊");
        break;

      default:
        USB_SERIAL.println("❓ Unknown command. Use w/s/r/p");
    }
  }

  delay(100);
}