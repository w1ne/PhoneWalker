// Position Evidence Firmware - PROVE servo moves with position readings
#include <Arduino.h>

void setup() {
  Serial.begin(115200);
  delay(2000);

  Serial.println("📍 POSITION EVIDENCE FIRMWARE");
  Serial.println("==============================");
  Serial.println("Will READ servo positions before/after commands");
  Serial.println("REAL EVIDENCE = Position changes!");

  Serial1.begin(1000000, SERIAL_8N1, 18, 17);
  delay(1000);

  Serial.println("\nCommands: t=test with position proof");
}

void sendCommand(uint8_t* packet, int length) {
  // Clear buffer
  while (Serial1.available()) Serial1.read();

  // Send command
  Serial1.write(packet, length);

  // Show what we sent
  Serial.printf("SENT: ");
  for (int i = 0; i < length; i++) {
    Serial.printf("%02X ", packet[i]);
  }
  Serial.println();

  // Wait for response
  delay(100);

  if (Serial1.available()) {
    Serial.printf("RESPONSE: ");
    while (Serial1.available()) {
      Serial.printf("%02X ", Serial1.read());
    }
    Serial.println();
  } else {
    Serial.println("NO RESPONSE");
  }
}

int readServoPosition(int servo_id) {
  Serial.printf("📖 Reading position from servo %d...\n", servo_id);

  // Read position command (correct format from working script)
  uint8_t read_cmd[] = {0xFF, 0xFF, (uint8_t)servo_id, 0x04, 0x02, 0x38, 0x02, 0x00};

  // Calculate checksum
  int sum = servo_id + 4 + 2 + 0x38 + 2;
  read_cmd[7] = (~sum) & 0xFF;

  // Clear buffer
  while (Serial1.available()) Serial1.read();

  // Send read command
  Serial1.write(read_cmd, 8);
  Serial.printf("Read command sent: ");
  for (int i = 0; i < 8; i++) {
    Serial.printf("%02X ", read_cmd[i]);
  }
  Serial.println();

  delay(100);

  // Read response
  if (Serial1.available() >= 7) {
    uint8_t response[10];
    int bytes_read = Serial1.readBytes(response, 10);

    Serial.printf("Position response (%d bytes): ", bytes_read);
    for (int i = 0; i < bytes_read; i++) {
      Serial.printf("%02X ", response[i]);
    }
    Serial.println();

    // Parse position if response is valid
    if (bytes_read >= 7 && response[0] == 0xFF && response[1] == 0xFF) {
      int position = response[5] | (response[6] << 8);
      Serial.printf("🎯 POSITION = %d\n", position);
      return position;
    } else {
      Serial.println("❌ Invalid response format");
    }
  } else {
    Serial.println("❌ NO POSITION RESPONSE");
  }

  return -1;  // Failed to read
}

void testWithPositionEvidence() {
  Serial.println("\n🔍 TESTING WITH POSITION EVIDENCE");
  Serial.println("==================================");

  int servo_id = 1;

  // Step 1: Read initial position
  Serial.println("STEP 1: Read initial position");
  int initial_pos = readServoPosition(servo_id);

  delay(1000);

  // Step 2: Enable torque
  Serial.println("\nSTEP 2: Enable torque");
  uint8_t torque_cmd[] = {0xFF, 0xFF, 0x01, 0x04, 0x03, 0x28, 0x01, 0xCC};
  sendCommand(torque_cmd, 8);

  delay(1000);

  // Step 3: Move to position 1500
  Serial.println("\nSTEP 3: Move to position 1500");
  uint8_t move_cmd[] = {0xFF, 0xFF, 0x01, 0x09, 0x03, 0x2A, 0x00, 0xDC, 0x05, 0xE8, 0x03, 0x00, 0x00, 0xFB};
  sendCommand(move_cmd, 14);

  Serial.println("⏰ Waiting 3 seconds for movement...");
  delay(3000);

  // Step 4: Read position after movement
  Serial.println("\nSTEP 4: Read position after movement");
  int final_pos = readServoPosition(servo_id);

  // Step 5: EVIDENCE ANALYSIS
  Serial.println("\n📊 EVIDENCE ANALYSIS");
  Serial.println("====================");
  Serial.printf("Initial position: %d\n", initial_pos);
  Serial.printf("Target position:  1500\n");
  Serial.printf("Final position:   %d\n", final_pos);

  if (initial_pos != -1 && final_pos != -1) {
    int change = abs(final_pos - initial_pos);
    int target_error = abs(final_pos - 1500);

    if (change > 50) {
      Serial.printf("✅ SERVO MOVED! Change = %d\n", change);

      if (target_error < 100) {
        Serial.println("🎯 REACHED TARGET! Servo control working!");
      } else {
        Serial.printf("⚠️ Moved but missed target by %d\n", target_error);
      }
      Serial.println("\n🎉 SUCCESS - Evidence complete");
    } else {
      Serial.println("❌ NO MOVEMENT DETECTED");
      Serial.println("\n❌ FAILED - Evidence complete");
    }
  } else {
    Serial.println("❌ CANNOT READ POSITIONS - Communication failed");
    Serial.println("\n❌ FAILED - Evidence complete");
  }
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();

    if (cmd == 't') {
      testWithPositionEvidence();
    } else if (cmd != '\n' && cmd != '\r') {
      Serial.printf("Unknown: %c\n", cmd);
    }
  }

  delay(100);
}