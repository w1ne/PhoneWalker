// PhoneWalker - Modular Servo Control System
#include <Arduino.h>
#include "config.h"
#include "servo_manager.h"
#include "command_handler.h"

// LED control (simplified for now - can be expanded to proper WS2812B later)
void setLED(uint8_t r, uint8_t g, uint8_t b) {
  // For now just set pin high/low for basic indication
  digitalWrite(LED_PIN, (r > 0 || g > 0 || b > 0) ? HIGH : LOW);
}

void setStatusLED(Color color) {
  setLED(color.r, color.g, color.b);
}

void setup() {
  Serial.begin(USB_UART_BAUD);
  delay(2000);

  // Initialize LED
  pinMode(LED_PIN, OUTPUT);
  setStatusLED(LED_STARTUP);

  // Print startup banner
  Serial.println("\n🤖 PHONEWALKER SERVO CONTROL SYSTEM");
  Serial.println("===================================");
  Serial.printf("Firmware Version: 2.0 - Modular Architecture\n");
  Serial.printf("Build Date: %s %s\n", __DATE__, __TIME__);
  Serial.println();

  // Initialize subsystems
  Serial.println("🔧 Initializing subsystems...");

  // Initialize servo manager
  servoManager.begin();

  // Initialize command handler
  cmdHandler.begin();

  // Perform initial servo scan
  Serial.println("\n🔍 Performing initial servo scan...");
  int found_servos = servoManager.scanServos();

  if (found_servos > 0) {
    Serial.printf("✅ System ready - %d servos detected\n", found_servos);
    setStatusLED(LED_READY);
  } else {
    Serial.println("⚠️ System ready - No servos detected");
    Serial.println("   Use 's' command to rescan");
    setStatusLED(LED_ERROR);
  }

  Serial.println("\n📋 Quick commands:");
  Serial.println("   h = Help and command reference");
  Serial.println("   s = Scan for servos");
  Serial.println("   d = Start basic dance");
  Serial.println("   t = Transparent mode");
  Serial.println();
}

void loop() {
  // Update subsystems
  cmdHandler.update();

  // Update status LED based on current mode
  static SystemMode lastMode = MODE_TRANSPARENT;
  SystemMode currentMode = cmdHandler.getMode();

  if (currentMode != lastMode) {
    switch (currentMode) {
      case MODE_TRANSPARENT:
        setStatusLED(LED_TRANSPARENT);
        break;
      case MODE_AUTONOMOUS:
        setStatusLED(LED_READY);
        break;
      case MODE_TESTING:
        setStatusLED(LED_TESTING);
        break;
      case MODE_DANCING:
        setStatusLED(LED_DANCING);
        break;
    }
    lastMode = currentMode;
  }

  // Small delay for stability
  delay(10);
}