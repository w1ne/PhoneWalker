// PhoneWalker Servo Management System
#ifndef SERVO_MANAGER_H
#define SERVO_MANAGER_H

#include <Arduino.h>
#include "config.h"

// Servo state tracking
struct ServoInfo {
  uint8_t id;
  bool detected;
  bool torque_enabled;
  uint16_t current_position;
  uint16_t target_position;
  unsigned long last_update;
  bool position_valid;
};

// Dance step definition
struct DanceStep {
  uint8_t servo_id;
  uint16_t position;
  uint16_t duration;
  uint16_t speed;
  const char* description;
};

// Dance sequence
struct DanceSequence {
  DanceStep* steps;
  int step_count;
  bool loop_enabled;
  int current_step;
  unsigned long last_step_time;
  bool active;
};

class ServoManager {
private:
  ServoInfo servos[MAX_SERVOS];
  int detected_servo_count;
  DanceSequence current_dance;

  // Protocol methods
  uint8_t calculateChecksum(uint8_t* data, int length);
  bool sendSTSCommand(uint8_t id, uint8_t instruction, uint8_t* params, int param_count);
  bool waitForResponse(uint8_t* buffer, int* length, int timeout = SERVO_RESPONSE_TIMEOUT);

public:
  ServoManager();

  // Initialization and scanning
  void begin();
  int scanServos(int start_id = SERVO_SCAN_START, int end_id = SERVO_SCAN_END);
  void printServoStatus();

  // Individual servo control
  bool pingServo(uint8_t id);
  bool enableTorque(uint8_t id, bool enable = true);
  bool moveServo(uint8_t id, uint16_t position, uint16_t time_ms = SERVO_DEFAULT_TIME, uint16_t speed = SERVO_DEFAULT_SPEED);
  int readPosition(uint8_t id);
  bool waitForPosition(uint8_t id, uint16_t target_position, int timeout = SERVO_MOVE_TIMEOUT);

  // Group control
  bool enableAllTorque(bool enable = true);
  bool moveAllServos(uint16_t position, uint16_t time_ms = SERVO_DEFAULT_TIME);
  bool centerAllServos();

  // Dance system
  bool loadDanceSequence(DanceStep* steps, int step_count, bool loop = true);
  bool startDance();
  bool stopDance();
  void updateDance(); // Call in main loop
  bool isDancing();

  // Status and diagnostics
  int getDetectedServoCount();
  ServoInfo* getServoInfo(uint8_t id);
  bool isServoDetected(uint8_t id);
  void updateAllPositions();

  // Utility
  static bool isValidPosition(uint16_t position);
  static uint16_t constrainPosition(uint16_t position);
};

// Global servo manager instance
extern ServoManager servoManager;

// Predefined dance sequences
extern DanceStep basicDanceSteps[];
extern DanceStep extremeDanceSteps[];
extern DanceStep coordinatedDanceSteps[];

#endif