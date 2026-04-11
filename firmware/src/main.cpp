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
  USB_SERIAL.println("Modes:");
  USB_SERIAL.println("  t = Transparent mode (UART passthrough)");
  USB_SERIAL.println("  d = Start autonomous dancing");
  USB_SERIAL.println("  s = Stop dancing");
  USB_SERIAL.println("  p = Ping test");
  USB_SERIAL.println("  r = Read positions");
  USB_SERIAL.println("  h = Help");

  // Initialize servo UART - CORRECTED pin assignment
  SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17); // RX=18, TX=17
  delay(1000);

  setLED(0, 255, 0); // Green = ready
  USB_SERIAL.println("✅ Ready - Default mode: TRANSPARENT");
}

// Send STS servo command with proper protocol
void sendSTSCommand(uint8_t id, uint8_t instruction, uint8_t *params, int param_count) {
  uint8_t packet[20];
  int length = 0;

  // Header
  packet[0] = 0xFF;
  packet[1] = 0xFF;
  packet[2] = id;
  packet[3] = param_count + 2; // Length = instruction + params + checksum
  packet[4] = instruction;

  length = 5;

  // Add parameters
  for (int i = 0; i < param_count; i++) {
    packet[length++] = params[i];
  }

  // Calculate checksum
  uint8_t sum = id + packet[3] + instruction;
  for (int i = 0; i < param_count; i++) {
    sum += params[i];
  }
  packet[length++] = (~sum) & 0xFF;

  // Send packet
  SERVO_SERIAL.write(packet, length);

  // Debug output
  USB_SERIAL.printf("SENT: ");
  for (int i = 0; i < length; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();

  delay(50);
}

// Enable servo torque
void enableTorque(uint8_t id) {
  uint8_t params[] = {0x28, 0x00, 0x01}; // Address 40 (0x28), enable
  sendSTSCommand(id, 0x03, params, 3);
  servoTorqueEnabled = true;
  USB_SERIAL.println("💪 Torque enabled");
}

// Move servo to position
void moveServo(uint8_t id, uint16_t position, uint16_t time_ms, uint16_t speed) {
  uint8_t params[] = {
    0x2A, 0x00,                    // Address 42 (0x2A) for position
    (uint8_t)(position & 0xFF),    // Position low byte
    (uint8_t)(position >> 8),      // Position high byte
    (uint8_t)(time_ms & 0xFF),     // Time low byte
    (uint8_t)(time_ms >> 8),       // Time high byte
    (uint8_t)(speed & 0xFF),       // Speed low byte
    (uint8_t)(speed >> 8)          // Speed high byte
  };
  sendSTSCommand(id, 0x03, params, 8);
  USB_SERIAL.printf("🎯 Moving to position %d\n", position);
}

// Read servo position
int readPosition(uint8_t id) {
  uint8_t params[] = {0x38, 0x02}; // Address 56 (0x38), read 2 bytes
  sendSTSCommand(id, 0x02, params, 2);

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

// Ping servo
void pingServo(uint8_t id) {
  sendSTSCommand(id, 0x01, nullptr, 0); // Ping command

  delay(100);

  if (SERVO_SERIAL.available() > 0) {
    USB_SERIAL.printf("PING RESPONSE: ");
    while (SERVO_SERIAL.available()) {
      USB_SERIAL.printf("%02X ", SERVO_SERIAL.read());
    }
    USB_SERIAL.println();
  } else {
    USB_SERIAL.println("❌ No ping response");
  }
}

// Dance sequence - autonomous mode
void performDance() {
  if (!servoTorqueEnabled) {
    enableTorque(1);
    delay(500);
  }

  // Dance positions and timing
  struct DanceMove {
    uint16_t position;
    uint16_t time_ms;
    const char* name;
  };

  static DanceMove danceSequence[] = {
    {2048, 1000, "Center"},      // Center position
    {1500, 800, "Left"},         // Left sweep
    {2500, 800, "Right"},        // Right sweep
    {1000, 1200, "Far Left"},    // Extreme left
    {3000, 1200, "Far Right"},   // Extreme right
    {2048, 1000, "Center"},      // Back to center
    {1800, 600, "Left Lean"},    // Quick movements
    {2300, 600, "Right Lean"},
    {2048, 1000, "Rest"}         // Rest position
  };

  static int sequenceLength = sizeof(danceSequence) / sizeof(DanceMove);

  if (millis() - lastDanceTime >= danceSequence[danceStep].time_ms) {
    DanceMove move = danceSequence[danceStep];

    setLED(255, 0, 255); // Purple during movement
    USB_SERIAL.printf("🕺 Dance step %d: %s (pos %d)\n",
                     danceStep + 1, move.name, move.position);

    moveServo(1, move.position, move.time_ms, 1000);

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

// Debug tests
void runDebugTest() {
  USB_SERIAL.println("🔧 Running debug tests...");

  setLED(255, 255, 0); // Yellow for testing

  // Test 1: Ping
  USB_SERIAL.println("\n1. Ping test:");
  pingServo(1);
  delay(500);

  // Test 2: Read position
  USB_SERIAL.println("\n2. Position read test:");
  readPosition(1);
  delay(500);

  // Test 3: Enable torque and test movement
  USB_SERIAL.println("\n3. Torque and movement test:");
  enableTorque(1);
  delay(1000);

  // Small movement test
  moveServo(1, 2048, 1000, 500);
  delay(2000);

  int pos = readPosition(1);
  if (pos > 0) {
    USB_SERIAL.printf("✅ Movement test completed - Position: %d\n", pos);
    setLED(0, 255, 0); // Green for success
  } else {
    USB_SERIAL.println("❌ Movement test failed");
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

      case 'h':
        USB_SERIAL.println("\n🤖 PHONEWALKER COMMANDS:");
        USB_SERIAL.println("  t = Transparent mode (UART passthrough)");
        USB_SERIAL.println("  d = Start autonomous dancing");
        USB_SERIAL.println("  s = Stop dancing");
        USB_SERIAL.println("  p = Ping test");
        USB_SERIAL.println("  r = Read positions");
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