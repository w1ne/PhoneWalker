// PhoneWalker Servo Management Implementation
#include "servo_manager.h"

// Global instance
ServoManager servoManager;

// Predefined dance sequences
#define BASIC_DANCE_STEPS 4
#define EXTREME_DANCE_STEPS 6
#define COORDINATED_DANCE_STEPS 6

DanceStep basicDanceSteps[BASIC_DANCE_STEPS] = {
  {1, 2048, 1000, 1000, "Center"},
  {1, 1500, 1000, 1000, "Left"},
  {1, 2500, 1000, 1000, "Right"},
  {1, 2048, 1500, 800, "Return to center"}
};

DanceStep extremeDanceSteps[EXTREME_DANCE_STEPS] = {
  {1, 2048, 1000, 1000, "Start center"},
  {1, 1000, 1500, 1200, "Far left"},
  {1, 3000, 1500, 1200, "Far right"},
  {1, 500, 1000, 1500, "Extreme left"},
  {1, 3500, 1000, 1500, "Extreme right"},
  {1, 2048, 2000, 800, "Rest center"}
};

DanceStep coordinatedDanceSteps[COORDINATED_DANCE_STEPS] = {
  {1, 1500, 1000, 1000, "Servo 1 left"},
  {2, 2500, 1000, 1000, "Servo 2 right"},
  {1, 2500, 1000, 1000, "Servo 1 right"},
  {2, 1500, 1000, 1000, "Servo 2 left"},
  {1, 2048, 1500, 800, "Servo 1 center"},
  {2, 2048, 1500, 800, "Servo 2 center"}
};

ServoManager::ServoManager() {
  detected_servo_count = 0;
  current_dance.steps = nullptr;
  current_dance.step_count = 0;
  current_dance.active = false;
  current_dance.current_step = 0;
  current_dance.loop_enabled = false;
  current_dance.last_step_time = 0;

  // Initialize servo info
  for (int i = 0; i < MAX_SERVOS; i++) {
    servos[i].id = i + 1;
    servos[i].detected = false;
    servos[i].torque_enabled = false;
    servos[i].current_position = SERVO_CENTER_POSITION;
    servos[i].target_position = SERVO_CENTER_POSITION;
    servos[i].last_update = 0;
    servos[i].position_valid = false;
  }
}

void ServoManager::begin() {
  Serial.println("🔧 ServoManager initializing...");

  // Initialize servo UART
  Serial1.begin(SERVO_UART_BAUD, SERIAL_8N1, SERVO_UART_RX, SERVO_UART_TX);
  delay(100);

  // Scan for servos
  int found = scanServos();

  Serial.printf("✅ ServoManager ready - %d servos detected\n", found);
}

uint8_t ServoManager::calculateChecksum(uint8_t* data, int length) {
  uint16_t sum = 0;
  for (int i = 0; i < length; i++) {
    sum += data[i];
  }
  return (~sum) & 0xFF;
}

bool ServoManager::sendSTSCommand(uint8_t id, uint8_t instruction, uint8_t* params, int param_count) {
  uint8_t packet[32];
  int packet_length = 0;

  // Build packet header
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = id;
  packet[3] = param_count + 2; // instruction + params + checksum
  packet[4] = instruction;
  packet_length = 5;

  // Add parameters
  for (int i = 0; i < param_count; i++) {
    packet[packet_length++] = params[i];
  }

  // Calculate and add checksum
  uint8_t checksum = calculateChecksum(&packet[2], packet_length - 2);
  packet[packet_length++] = checksum;

  // Clear receive buffer
  while (Serial1.available()) {
    Serial1.read();
  }

  // Send packet
  Serial1.write(packet, packet_length);

  if (DEBUG_PROTOCOL) {
    Serial.printf("SENT [%d]: ", id);
    for (int i = 0; i < packet_length; i++) {
      Serial.printf("%02X ", packet[i]);
    }
    Serial.println();
  }

  return true;
}

bool ServoManager::waitForResponse(uint8_t* buffer, int* length, int timeout) {
  unsigned long start = millis();
  int received = 0;

  while (millis() - start < timeout && received < RESPONSE_BUFFER_SIZE - 1) {
    if (Serial1.available()) {
      buffer[received++] = Serial1.read();
    }
    delay(1);
  }

  *length = received;

  if (DEBUG_PROTOCOL && received > 0) {
    Serial.printf("RECV: ");
    for (int i = 0; i < received; i++) {
      Serial.printf("%02X ", buffer[i]);
    }
    Serial.println();
  }

  return received > 0;
}

bool ServoManager::pingServo(uint8_t id) {
  if (id < 1 || id > MAX_SERVOS) return false;

  // Send ping command
  sendSTSCommand(id, 0x01, nullptr, 0);

  // Wait for response
  uint8_t response[RESPONSE_BUFFER_SIZE];
  int response_length;

  if (waitForResponse(response, &response_length)) {
    if (response_length >= 6 && response[0] == 0xFF && response[1] == 0xFF) {
      servos[id-1].detected = true;
      return true;
    }
  }

  return false;
}

int ServoManager::scanServos(int start_id, int end_id) {
  Serial.printf("🔍 Scanning servos %d-%d...\n", start_id, end_id);

  detected_servo_count = 0;

  for (int id = start_id; id <= end_id; id++) {
    if (DEBUG_SERVO_SCAN) {
      Serial.printf("Ping servo %d: ", id);
    }

    if (pingServo(id)) {
      detected_servo_count++;
      if (DEBUG_SERVO_SCAN) {
        Serial.println("✅ FOUND");
      }
    } else {
      servos[id-1].detected = false;
      if (DEBUG_SERVO_SCAN) {
        Serial.println("❌ Not found");
      }
    }

    delay(50); // Small delay between pings
  }

  Serial.printf("📊 Scan complete: %d servos detected\n", detected_servo_count);
  return detected_servo_count;
}

bool ServoManager::enableTorque(uint8_t id, bool enable) {
  if (id < 1 || id > MAX_SERVOS || !servos[id-1].detected) return false;

  uint8_t params[] = {40, 0, enable ? (uint8_t)1 : (uint8_t)0}; // Address 40 = Torque Enable
  sendSTSCommand(id, 0x03, params, 3);

  servos[id-1].torque_enabled = enable;

  if (DEBUG_PROTOCOL) {
    Serial.printf("💪 Servo %d torque %s\n", id, enable ? "enabled" : "disabled");
  }

  return true;
}

bool ServoManager::moveServo(uint8_t id, uint16_t position, uint16_t time_ms, uint16_t speed) {
  if (id < 1 || id > MAX_SERVOS || !servos[id-1].detected) return false;

  position = constrainPosition(position);

  uint8_t params[] = {
    42, 0,                           // Address 42 = Goal Position
    (uint8_t)(position & 0xFF),      // Position low byte
    (uint8_t)(position >> 8),        // Position high byte
    (uint8_t)(time_ms & 0xFF),       // Time low byte
    (uint8_t)(time_ms >> 8),         // Time high byte
    (uint8_t)(speed & 0xFF),         // Speed low byte
    (uint8_t)(speed >> 8)            // Speed high byte
  };

  sendSTSCommand(id, 0x03, params, 8);

  servos[id-1].target_position = position;

  if (DEBUG_PROTOCOL) {
    Serial.printf("🎯 Servo %d → %d (time=%dms, speed=%d)\n", id, position, time_ms, speed);
  }

  return true;
}

int ServoManager::readPosition(uint8_t id) {
  if (id < 1 || id > MAX_SERVOS || !servos[id-1].detected) return -1;

  uint8_t params[] = {56, 0, 2, 0}; // Address 56 = Present Position, read 2 bytes
  sendSTSCommand(id, 0x02, params, 4);

  uint8_t response[RESPONSE_BUFFER_SIZE];
  int response_length;

  if (waitForResponse(response, &response_length)) {
    if (response_length >= 7 && response[0] == 0xFF && response[1] == 0xFF) {
      uint16_t position = response[5] | (response[6] << 8);

      servos[id-1].current_position = position;
      servos[id-1].position_valid = true;
      servos[id-1].last_update = millis();

      if (DEBUG_POSITION_READS) {
        Serial.printf("📍 Servo %d position: %d\n", id, position);
      }

      return position;
    }
  }

  servos[id-1].position_valid = false;
  return -1;
}

bool ServoManager::enableAllTorque(bool enable) {
  bool success = true;

  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servos[i].detected) {
      success &= enableTorque(servos[i].id, enable);
      delay(50);
    }
  }

  return success;
}

bool ServoManager::moveAllServos(uint16_t position, uint16_t time_ms) {
  bool success = true;

  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servos[i].detected) {
      success &= moveServo(servos[i].id, position, time_ms);
      delay(10);
    }
  }

  return success;
}

bool ServoManager::centerAllServos() {
  Serial.println("🎯 Centering all servos...");
  return moveAllServos(SERVO_CENTER_POSITION, SERVO_DEFAULT_TIME);
}

bool ServoManager::loadDanceSequence(DanceStep* steps, int step_count, bool loop) {
  current_dance.steps = steps;
  current_dance.step_count = step_count;
  current_dance.loop_enabled = loop;
  current_dance.current_step = 0;
  current_dance.active = false;
  current_dance.last_step_time = 0;

  Serial.printf("💃 Dance loaded: %d steps, loop=%s\n", step_count, loop ? "yes" : "no");
  return true;
}

bool ServoManager::startDance() {
  if (current_dance.steps == nullptr || current_dance.step_count == 0) {
    Serial.println("❌ No dance sequence loaded");
    return false;
  }

  // Enable torque for all dancing servos
  for (int i = 0; i < current_dance.step_count; i++) {
    uint8_t servo_id = current_dance.steps[i].servo_id;
    if (servo_id >= 1 && servo_id <= MAX_SERVOS && servos[servo_id-1].detected) {
      enableTorque(servo_id, true);
      delay(100);
    }
  }

  current_dance.active = true;
  current_dance.current_step = 0;
  current_dance.last_step_time = millis();

  Serial.println("🕺 Dance started!");
  return true;
}

bool ServoManager::stopDance() {
  current_dance.active = false;
  Serial.println("⏹️ Dance stopped");
  return true;
}

void ServoManager::updateDance() {
  if (!current_dance.active || current_dance.steps == nullptr) return;

  unsigned long now = millis();
  DanceStep& step = current_dance.steps[current_dance.current_step];

  if (now - current_dance.last_step_time >= step.duration) {
    // Execute current dance step
    if (servos[step.servo_id-1].detected) {
      moveServo(step.servo_id, step.position, step.duration, step.speed);

      if (DEBUG_DANCE_MOVES) {
        Serial.printf("💃 Step %d: %s\n", current_dance.current_step + 1, step.description);
      }
    }

    // Move to next step
    current_dance.current_step++;
    current_dance.last_step_time = now;

    // Handle sequence end
    if (current_dance.current_step >= current_dance.step_count) {
      if (current_dance.loop_enabled) {
        current_dance.current_step = 0;
        Serial.println("🔄 Dance sequence looping...");
      } else {
        current_dance.active = false;
        Serial.println("🏁 Dance sequence completed");
      }
    }
  }
}

bool ServoManager::isDancing() {
  return current_dance.active;
}

int ServoManager::getDetectedServoCount() {
  return detected_servo_count;
}

ServoInfo* ServoManager::getServoInfo(uint8_t id) {
  if (id < 1 || id > MAX_SERVOS) return nullptr;
  return &servos[id-1];
}

bool ServoManager::isServoDetected(uint8_t id) {
  if (id < 1 || id > MAX_SERVOS) return false;
  return servos[id-1].detected;
}

void ServoManager::updateAllPositions() {
  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servos[i].detected) {
      readPosition(servos[i].id);
      delay(50);
    }
  }
}

bool ServoManager::isValidPosition(uint16_t position) {
  return position >= SERVO_MIN_POSITION && position <= SERVO_MAX_POSITION;
}

uint16_t ServoManager::constrainPosition(uint16_t position) {
  if (position < SERVO_MIN_POSITION) return SERVO_MIN_POSITION;
  if (position > SERVO_MAX_POSITION) return SERVO_MAX_POSITION;
  return position;
}

void ServoManager::printServoStatus() {
  Serial.println("\n📊 SERVO STATUS REPORT");
  Serial.println("======================");

  for (int i = 0; i < MAX_SERVOS; i++) {
    if (servos[i].detected) {
      Serial.printf("Servo %d: ", servos[i].id);
      Serial.printf("pos=%d, ", servos[i].current_position);
      Serial.printf("target=%d, ", servos[i].target_position);
      Serial.printf("torque=%s, ", servos[i].torque_enabled ? "ON" : "OFF");
      Serial.printf("valid=%s\n", servos[i].position_valid ? "YES" : "NO");
    }
  }

  Serial.printf("\nTotal: %d servos detected\n", detected_servo_count);
}