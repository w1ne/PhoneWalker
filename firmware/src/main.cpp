// PhoneWalker Dancing Firmware with Debug Modes
// Combines autonomous dancing + transparent mode for debugging

#include <Arduino.h>

#define LED_PIN 21
#define USB_SERIAL Serial
#define SERVO_SERIAL Serial1

// Mode states
enum Mode {
  TRANSPARENT_MODE,
  AUTONOMOUS_DANCE,
  DEBUG_TEST
};

Mode currentMode = TRANSPARENT_MODE;
unsigned long lastDanceTime = 0;
int danceStep = 0;
bool servoTorqueEnabled = false;

// RGB LED control
void setLED(uint8_t r, uint8_t g, uint8_t b) {
  // Simple bit-bang for WS2812B on GPIO21
  // This is a simplified version - proper implementation needs precise timing
  digitalWrite(LED_PIN, LOW);
  delay(1);
}

void setup() {
  USB_SERIAL.begin(115200);
  delay(2000);

  // Initialize LED pin
  pinMode(LED_PIN, OUTPUT);
  setLED(255, 0, 0); // Red = starting up

  USB_SERIAL.println("🤖 PHONEWALKER DANCING FIRMWARE");
  USB_SERIAL.println("===============================");
  USB_SERIAL.println("Commands:");
  USB_SERIAL.println("  t = Transparent mode (UART passthrough)");
  USB_SERIAL.println("  d = Start autonomous dancing");
  USB_SERIAL.println("  s = Stop dancing");
  USB_SERIAL.println("  p = Ping test");
  USB_SERIAL.println("  r = Read positions");
  USB_SERIAL.println("  x = Comprehensive test with evidence");
  USB_SERIAL.println("  h = Help");

  // Initialize servo UART - CORRECTED pin assignment
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  setLED(0, 255, 0); // Green = ready
  USB_SERIAL.println("✅ Ready - Default mode: TRANSPARENT");
}

// Send STS servo command - EXACT working protocol
void sendSTSCommand(uint8_t id, uint8_t instruction, uint8_t p1=0, uint8_t p2=0, uint8_t p3=0, uint8_t p4=0, uint8_t p5=0, uint8_t p6=0, uint8_t p7=0, uint8_t p8=0) {
  uint8_t packet[20];
  int length = 0;
  uint8_t checksum = 0;

  // Header
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = id;

  if (instruction == 1) {
    // PING command - EXACT working format
    packet[3] = 2;  // Length 2
    packet[4] = 1;  // PING instruction
    length = 5;
    checksum = (~(id + 2 + 1)) & 0xFF;

  } else if (instruction == 3 && p1 == 40) {
    // Enable torque - EXACT working format
    packet[3] = 4;  // Length 4
    packet[4] = 3;  // Write instruction
    packet[5] = 40; // Torque address
    packet[6] = 0;
    packet[7] = p3; // Enable value
    length = 8;
    checksum = (~(id + 4 + 3 + 40 + 0 + p3)) & 0xFF;

  } else if (instruction == 3 && p1 == 42) {
    // Set position - EXACT working format
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

  } else if (instruction == 2) {
    // Read position - EXACT working format
    packet[3] = 6;  // Length 6
    packet[4] = 2;  // Read instruction
    packet[5] = 56; // Position address (0x38)
    packet[6] = 0;
    packet[7] = 2;  // Read 2 bytes
    packet[8] = 0;
    length = 9;
    checksum = (~(id + 6 + 2 + 56 + 0 + 2 + 0)) & 0xFF;
  }

  packet[length] = checksum;
  length++;

  // Send packet
  SERVO_SERIAL.write(packet, length);

  // Debug output
  USB_SERIAL.printf("SENT (%d bytes): ", length);
  for (int i = 0; i < length; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();

  delay(50);
}

// Enable servo torque
void enableTorque(uint8_t id) {
  sendSTSCommand(id, 3, 40, 0, 1);  // Enable torque using exact working format
  servoTorqueEnabled = true;
  USB_SERIAL.println("💪 Torque enabled");
}

// Move servo to position - EXACT working format
void moveServo(uint8_t id, uint16_t position, uint16_t time_ms = 1000, uint16_t speed = 1000) {
  uint8_t pos_l = position & 0xFF;
  uint8_t pos_h = (position >> 8) & 0xFF;
  uint8_t time_l = time_ms & 0xFF;
  uint8_t time_h = (time_ms >> 8) & 0xFF;
  uint8_t speed_l = speed & 0xFF;
  uint8_t speed_h = (speed >> 8) & 0xFF;

  sendSTSCommand(id, 3, 42, 0, pos_l, pos_h, time_l, time_h, speed_l, speed_h);
  USB_SERIAL.printf("🎯 Moving to position %d (time=%dms)\n", position, time_ms);
}

// Read servo position - EXACT working format
int readPosition(uint8_t id) {
  // Clear any existing data first
  while (SERVO_SERIAL.available()) {
    SERVO_SERIAL.read();
  }

  sendSTSCommand(id, 2, 56, 0, 2, 0);  // Read 2 bytes from address 56

  delay(100);

  if (SERVO_SERIAL.available() >= 7) {
    uint8_t response[10];
    int bytes_read = SERVO_SERIAL.readBytes(response, 10);

    USB_SERIAL.printf("RESPONSE: ");
    for (int i = 0; i < bytes_read; i++) {
      USB_SERIAL.printf("%02X ", response[i]);
    }
    USB_SERIAL.println();

    if (bytes_read >= 7 && response[0] == 0xFF && response[1] == 0xFF) {
      int position = response[5] | (response[6] << 8);
      USB_SERIAL.printf("📍 Position: %d\n", position);
      return position;
    }
  }

  USB_SERIAL.println("❌ Failed to read position");
  return -1;
}

// Ping servo - EXACT working format
void pingServo(uint8_t id) {
  // Clear any existing data first
  while (SERVO_SERIAL.available()) {
    SERVO_SERIAL.read();
  }

  sendSTSCommand(id, 1);  // Ping command with exact working format

  delay(100);

  if (SERVO_SERIAL.available() > 0) {
    USB_SERIAL.printf("PING RESPONSE: ");
    while (SERVO_SERIAL.available()) {
      USB_SERIAL.printf("%02X ", SERVO_SERIAL.read());
    }
    USB_SERIAL.println();
    USB_SERIAL.printf("✅ Servo %d responded\n", id);
  } else {
    USB_SERIAL.printf("❌ No ping response from servo %d\n", id);
  }
}

// Dance sequence - autonomous mode
void performDance() {
  if (!servoTorqueEnabled) {
    enableTorque(1);
    delay(500);
  }

  // Dance positions using EXACT working values from test script
  struct DanceMove {
    uint16_t position;
    uint16_t time_ms;
    const char* name;
  };

  static DanceMove danceSequence[] = {
    {2048, 1000, "Center"},      // Center position (proven working)
    {1500, 1000, "Left"},        // Left position (proven working)
    {2500, 1000, "Right"},       // Right position (proven working)
    {2048, 1000, "Center"},      // Back to center
    {1000, 1200, "Far Left"},    // Extreme positions
    {3000, 1200, "Far Right"},
    {2048, 1500, "Rest"}         // Return to center and rest
  };

  static int sequenceLength = sizeof(danceSequence) / sizeof(DanceMove);

  if (millis() - lastDanceTime >= danceSequence[danceStep].time_ms) {
    DanceMove move = danceSequence[danceStep];

    setLED(255, 0, 255); // Purple during movement
    USB_SERIAL.printf("🕺 Dance step %d: %s (pos %d)\n",
                     danceStep + 1, move.name, move.position);

    // Use exact working format with proper timing
    moveServo(1, move.position, move.time_ms);

    danceStep = (danceStep + 1) % sequenceLength;
    lastDanceTime = millis();

    delay(100);
    setLED(0, 0, 255); // Blue when dancing
  }
}

// Transparent mode - UART passthrough for debugging
void handleTransparentMode() {
  static bool ledState = false;
  static unsigned long lastBlink = 0;

  // Blink yellow LED in transparent mode
  if (millis() - lastBlink > 500) {
    setLED(ledState ? 255 : 0, ledState ? 255 : 0, 0);
    ledState = !ledState;
    lastBlink = millis();
  }

  // Forward USB to Servo
  if (USB_SERIAL.available()) {
    SERVO_SERIAL.write(USB_SERIAL.read());
  }

  // Forward Servo to USB
  if (SERVO_SERIAL.available()) {
    USB_SERIAL.write(SERVO_SERIAL.read());
  }
}

// Debug tests with position evidence
void runDebugTest() {
  USB_SERIAL.println("🔧 COMPREHENSIVE SERVO TEST");
  USB_SERIAL.println("===========================");

  setLED(255, 255, 0); // Yellow for testing

  // Test 1: Scan for working servos (like working script)
  USB_SERIAL.println("\n🔍 Scanning servos 1-4...");
  int workingServos[4];
  int workingCount = 0;

  for (int id = 1; id <= 4; id++) {
    USB_SERIAL.printf("Servo %d: ", id);

    // Clear buffer
    while (SERVO_SERIAL.available()) SERVO_SERIAL.read();

    pingServo(id);
    delay(500);

    // Check if we got a response
    bool responded = false;
    if (SERVO_SERIAL.available() > 0) {
      responded = true;
      workingServos[workingCount++] = id;
      USB_SERIAL.println("WORKING ✅");
    } else {
      USB_SERIAL.println("Not found ❌");
    }
    delay(200);
  }

  USB_SERIAL.printf("\n📊 Found %d working servos\n", workingCount);

  if (workingCount > 0) {
    // Test movement with position evidence
    int testServo = workingServos[0];
    USB_SERIAL.printf("\n🎯 Testing movement on servo %d with position evidence...\n", testServo);

    // Step 1: Read initial position
    USB_SERIAL.println("STEP 1: Reading initial position");
    int initialPos = readPosition(testServo);
    delay(1000);

    // Step 2: Enable torque
    USB_SERIAL.println("\nSTEP 2: Enabling torque");
    enableTorque(testServo);
    delay(1000);

    // Step 3: Move to test positions and verify
    int testPositions[] = {2048, 1500, 2500, 2048};
    const char* posNames[] = {"Center", "Left", "Right", "Center"};

    for (int i = 0; i < 4; i++) {
      USB_SERIAL.printf("\nSTEP %d: Moving to %s (%d)\n", i + 3, posNames[i], testPositions[i]);
      moveServo(testServo, testPositions[i], 1000);
      delay(2000);

      int finalPos = readPosition(testServo);
      if (finalPos > 0) {
        int error = abs(finalPos - testPositions[i]);
        USB_SERIAL.printf("📍 Reached position: %d (error: %d)\n", finalPos, error);
        if (error < 50) {
          USB_SERIAL.println("✅ Position reached successfully");
        } else {
          USB_SERIAL.println("⚠️ Large position error");
        }
      }
      delay(1000);
    }

    USB_SERIAL.println("\n🎉 MOVEMENT TEST COMPLETED");
    setLED(0, 255, 0); // Green for success
  } else {
    USB_SERIAL.println("\n❌ NO WORKING SERVOS FOUND");
    USB_SERIAL.println("Check connections and power");
    setLED(255, 0, 0); // Red for failure
  }

  currentMode = TRANSPARENT_MODE;
  USB_SERIAL.println("\nReturning to transparent mode");
}

void loop() {
  // Handle mode-specific behavior
  switch (currentMode) {
    case TRANSPARENT_MODE:
      handleTransparentMode();
      break;

    case AUTONOMOUS_DANCE:
      performDance();
      break;

    case DEBUG_TEST:
      runDebugTest();
      break;
  }

  // Handle commands
  if (USB_SERIAL.available()) {
    char cmd = USB_SERIAL.read();

    switch (cmd) {
      case 't':
        currentMode = TRANSPARENT_MODE;
        setLED(255, 255, 0); // Yellow for transparent
        USB_SERIAL.println("🔄 Switched to TRANSPARENT mode");
        break;

      case 'd':
        currentMode = AUTONOMOUS_DANCE;
        danceStep = 0;
        lastDanceTime = 0;
        setLED(0, 0, 255); // Blue for dancing
        USB_SERIAL.println("🕺 Starting AUTONOMOUS DANCE mode!");
        break;

      case 's':
        currentMode = TRANSPARENT_MODE;
        setLED(255, 255, 0); // Back to yellow
        USB_SERIAL.println("⏹️ Dance stopped - Back to transparent mode");
        break;

      case 'p':
        USB_SERIAL.println("📡 Ping test:");
        pingServo(1);
        break;

      case 'r':
        USB_SERIAL.println("📍 Reading positions:");
        for (int id = 1; id <= 4; id++) {
          USB_SERIAL.printf("Servo %d: ", id);
          readPosition(id);
          delay(200);
        }
        break;

      case 'x':
        USB_SERIAL.println("🧪 Running comprehensive test...");
        currentMode = DEBUG_TEST;
        break;

      case 'h':
        USB_SERIAL.println("\n🤖 PHONEWALKER COMMANDS:");
        USB_SERIAL.println("  t = Transparent mode (UART passthrough)");
        USB_SERIAL.println("  d = Start autonomous dancing");
        USB_SERIAL.println("  s = Stop dancing");
        USB_SERIAL.println("  p = Ping test");
        USB_SERIAL.println("  r = Read positions");
        USB_SERIAL.println("  x = Comprehensive test with evidence");
        USB_SERIAL.println("  h = Help");
        break;

      case '\n':
      case '\r':
        break;

      default:
        if (currentMode == TRANSPARENT_MODE) {
          // In transparent mode, forward the character
          SERVO_SERIAL.write(cmd);
        } else {
          USB_SERIAL.printf("Unknown command: %c (use 'h' for help)\n", cmd);
        }
    }
  }

  delay(10); // Small delay for stability
}