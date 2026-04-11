// PhoneWalker Dancing Firmware - FIXED
// Autonomous servo control with proper SCServo protocol

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
  {2048, 1000, "Center"},
  {1500, 800, "Left"},
  {2500, 800, "Right"},
  {1800, 600, "Mid-Left"},
  {2300, 600, "Mid-Right"},
  {2048, 1000, "Center"},
  {0, 0, "END"}
};

ServoMove shake_dance[] = {
  {2048, 500, "Start"},
  {1700, 300, "Shake-L1"},
  {2400, 300, "Shake-R1"},
  {1700, 250, "Shake-L2"},
  {2400, 250, "Shake-R2"},
  {2048, 500, "Stop"},
  {0, 0, "END"}
};

void sendServoCommand(int servo_id, uint8_t instruction, uint8_t* params, int param_length) {
  uint8_t length = param_length + 2; // instruction + checksum

  // Build packet: [0xFF, 0xFF, ID, LENGTH, INSTRUCTION, PARAMS..., CHECKSUM]
  USB_SERIAL.write(0xFF);
  USB_SERIAL.write(0xFF);
  USB_SERIAL.write((uint8_t)servo_id);
  USB_SERIAL.write(length);
  USB_SERIAL.write(instruction);

  // Write to SERVO_SERIAL too
  SERVO_SERIAL.write(0xFF);
  SERVO_SERIAL.write(0xFF);
  SERVO_SERIAL.write((uint8_t)servo_id);
  SERVO_SERIAL.write(length);
  SERVO_SERIAL.write(instruction);

  // Calculate checksum starting from ID
  int sum = servo_id + length + instruction;

  // Send parameters
  for (int i = 0; i < param_length; i++) {
    USB_SERIAL.write(params[i]);
    SERVO_SERIAL.write(params[i]);
    sum += params[i];
  }

  // Send checksum
  uint8_t checksum = (~sum) & 0xFF;
  USB_SERIAL.write(checksum);
  SERVO_SERIAL.write(checksum);

  USB_SERIAL.printf(" [Cmd sent: ID=%d, Inst=%d, Len=%d, CS=%02X]\n", servo_id, instruction, length, checksum);
}

void enableTorque(int servo_id) {
  USB_SERIAL.printf("💪 Enabling torque for servo %d", servo_id);

  // Address 40 (0x28) = Torque Enable, Value = 1
  uint8_t params[] = {40, 0, 1};
  sendServoCommand(servo_id, 0x03, params, 3);
  delay(200);
}

void moveServo(int servo_id, int position, int time_ms) {
  USB_SERIAL.printf("🎯 Moving servo %d to %d (%dms)", servo_id, position, time_ms);

  uint8_t pos_l = position & 0xFF;
  uint8_t pos_h = (position >> 8) & 0xFF;
  uint8_t time_l = time_ms & 0xFF;
  uint8_t time_h = (time_ms >> 8) & 0xFF;

  // Address 42 (0x2A) = Goal Position
  uint8_t params[] = {42, 0, pos_l, pos_h, time_l, time_h, 0, 0};
  sendServoCommand(servo_id, 0x03, params, 8);
}

void performDance(ServoMove* dance, const char* dance_name, int servo_id) {
  USB_SERIAL.printf("\n🕺 Starting %s Dance! 🕺\n", dance_name);
  USB_SERIAL.println("=================================");

  // Enable torque first
  enableTorque(servo_id);

  // Execute dance moves
  int move_count = 0;
  while (dance[move_count].time_ms != 0) {
    ServoMove* move = &dance[move_count];

    USB_SERIAL.printf("🎭 Move %d: %s\n", move_count + 1, move->name);
    moveServo(servo_id, move->position, move->time_ms);

    // Wait for completion
    delay(move->time_ms + 500);

    move_count++;
  }

  USB_SERIAL.printf("🎊 %s Dance Complete! 🎊\n\n", dance_name);
}

void setup() {
  // Initialize USB serial
  USB_SERIAL.begin(115200);
  delay(2000);

  USB_SERIAL.println("🎭 PhoneWalker Dancing Firmware - FIXED 🎭");
  USB_SERIAL.println("==========================================");
  USB_SERIAL.println("Autonomous servo dancing with proper SCServo protocol");

  // Initialize servo communication with CORRECT pins
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17 (FIXED!)
  delay(1000);

  USB_SERIAL.println("🎵 Ready to dance! Commands:");
  USB_SERIAL.println("  w = Wave dance");
  USB_SERIAL.println("  s = Shake dance");
  USB_SERIAL.println("  t = Test single move");
  USB_SERIAL.println();
}

void loop() {
  if (USB_SERIAL.available()) {
    char command = USB_SERIAL.read();
    int servo_id = 1;

    switch (command) {
      case 'w':
        performDance(wave_dance, "Wave", servo_id);
        break;

      case 's':
        performDance(shake_dance, "Shake", servo_id);
        break;

      case 't':
        USB_SERIAL.println("🔧 Single move test");
        enableTorque(servo_id);
        moveServo(servo_id, 1500, 1000);
        delay(2000);
        moveServo(servo_id, 2500, 1000);
        delay(2000);
        moveServo(servo_id, 2048, 1000);
        USB_SERIAL.println("✅ Test complete");
        break;

      case '\n':
      case '\r':
        // Ignore newlines
        break;

      default:
        USB_SERIAL.printf("❓ Unknown command '%c'. Use w/s/t\n", command);
    }
  }

  delay(100);
}