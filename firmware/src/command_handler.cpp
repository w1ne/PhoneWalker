// PhoneWalker Command Handler Implementation
#include "command_handler.h"
#include "config.h"

// Global instance
CommandHandler cmdHandler;

// Static array for commands (avoid dynamic allocation)
static Command command_list[32];

CommandHandler::CommandHandler() {
  commands = command_list;
  command_count = 0;
  current_mode = MODE_TRANSPARENT;
  command_buffer = "";
}

void CommandHandler::begin() {
  Serial.println("🎮 CommandHandler initializing...");
  registerBuiltinCommands();
  setMode(MODE_TRANSPARENT);
  Serial.println("✅ CommandHandler ready");
}

void CommandHandler::registerBuiltinCommands() {
  addCommand('h', "help", "Show this help message", cmdHelp);
  addCommand('t', "transparent", "Enter transparent mode (UART passthrough)", cmdTransparent);
  addCommand('s', "scan", "Scan for servos", cmdScan);
  addCommand('p', "ping", "Ping servo (usage: p [id])", cmdPing);
  addCommand('e', "enable", "Enable/disable torque (usage: e [id] [0/1])", cmdEnable);
  addCommand('m', "move", "Move servo (usage: m [id] [position] [time])", cmdMove);
  addCommand('r', "read", "Read servo position (usage: r [id])", cmdRead);
  addCommand('c', "center", "Center all servos", cmdCenter);
  addCommand('i', "status", "Show servo status", cmdStatus);
  addCommand('x', "test", "Run comprehensive test", cmdTest);
  addCommand('d', "dance", "Start dancing (usage: d [basic/extreme/coordinated])", cmdDance);
  addCommand('q', "stop", "Stop current action", cmdStop);
  addCommand('g', "config", "Show configuration", cmdConfig);
  addCommand('z', "debug", "Toggle debug modes (usage: z [protocol/scan/dance/position])", cmdDebug);
}

void CommandHandler::update() {
  // Handle mode-specific behavior
  switch (current_mode) {
    case MODE_TRANSPARENT:
      handleTransparentMode();
      break;
    case MODE_DANCING:
      servoManager.updateDance();
      if (!servoManager.isDancing()) {
        setMode(MODE_AUTONOMOUS);
      }
      break;
    case MODE_AUTONOMOUS:
    case MODE_TESTING:
      // Normal command processing
      break;
  }

  // Process incoming commands
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (command_buffer.length() > 0) {
        char cmd = command_buffer.charAt(0);
        String args = command_buffer.substring(1);
        args.trim();

        processCommand(cmd, args);
        command_buffer = "";
      }
    } else if (c >= ' ' && c <= '~') { // Printable characters only
      if (current_mode == MODE_TRANSPARENT && command_buffer.length() == 0) {
        // In transparent mode, forward single characters immediately
        Serial1.write(c);
      } else {
        command_buffer += c;
      }
    }
  }
}

void CommandHandler::setMode(SystemMode mode) {
  SystemMode old_mode = current_mode;
  current_mode = mode;

  const char* mode_names[] = {"TRANSPARENT", "AUTONOMOUS", "TESTING", "DANCING"};
  Serial.printf("🔄 Mode: %s → %s\n", mode_names[old_mode], mode_names[mode]);

  // Mode-specific setup
  switch (mode) {
    case MODE_TRANSPARENT:
      // Set LED to yellow
      break;
    case MODE_AUTONOMOUS:
      // Set LED to green
      break;
    case MODE_TESTING:
      // Set LED to purple
      break;
    case MODE_DANCING:
      // Set LED to blue
      break;
  }
}

SystemMode CommandHandler::getMode() {
  return current_mode;
}

void CommandHandler::processCommand(char cmd, const String& args) {
  // Find and execute command
  for (int i = 0; i < command_count; i++) {
    if (commands[i].key == cmd) {
      commands[i].function(args);
      return;
    }
  }

  // Unknown command
  if (current_mode == MODE_TRANSPARENT) {
    // In transparent mode, forward unknown commands to servo
    Serial1.write(cmd);
    if (args.length() > 0) {
      Serial1.print(args);
    }
  } else {
    Serial.printf("❌ Unknown command: '%c' (use 'h' for help)\n", cmd);
  }
}

void CommandHandler::handleTransparentMode() {
  // Forward data between USB and servo UART
  while (Serial1.available()) {
    Serial.write(Serial1.read());
  }
}

void CommandHandler::addCommand(char key, const char* name, const char* description, CommandFunction func, bool show_in_help) {
  if (command_count >= 32) {
    Serial.println("❌ Command table full!");
    return;
  }

  commands[command_count].key = key;
  commands[command_count].name = name;
  commands[command_count].description = description;
  commands[command_count].function = func;
  commands[command_count].show_in_help = show_in_help;
  command_count++;
}

void CommandHandler::removeCommand(char key) {
  for (int i = 0; i < command_count; i++) {
    if (commands[i].key == key) {
      // Shift remaining commands down
      for (int j = i; j < command_count - 1; j++) {
        commands[j] = commands[j + 1];
      }
      command_count--;
      break;
    }
  }
}

// Command implementations
void CommandHandler::cmdHelp(const String& args) {
  Serial.println("\n🤖 PHONEWALKER COMMAND REFERENCE");
  Serial.println("================================");

  for (int i = 0; i < cmdHandler.command_count; i++) {
    if (cmdHandler.commands[i].show_in_help) {
      Serial.printf("  %c = %s\n",
                   cmdHandler.commands[i].key,
                   cmdHandler.commands[i].description);
    }
  }

  Serial.printf("\nCurrent mode: %s\n",
               cmdHandler.current_mode == MODE_TRANSPARENT ? "TRANSPARENT" :
               cmdHandler.current_mode == MODE_AUTONOMOUS ? "AUTONOMOUS" :
               cmdHandler.current_mode == MODE_TESTING ? "TESTING" : "DANCING");

  Serial.printf("Detected servos: %d\n", servoManager.getDetectedServoCount());
}

void CommandHandler::cmdTransparent(const String& args) {
  cmdHandler.setMode(MODE_TRANSPARENT);
  Serial.println("🔄 Switched to transparent mode (UART passthrough)");
  Serial.println("   All commands forwarded to servo UART");
}

void CommandHandler::cmdScan(const String& args) {
  Serial.println("🔍 Scanning for servos...");
  int found = servoManager.scanServos();
  Serial.printf("📊 Scan complete: %d servos found\n", found);
  cmdHandler.setMode(MODE_AUTONOMOUS);
}

void CommandHandler::cmdPing(const String& args) {
  if (args.length() == 0) {
    // Ping all detected servos
    Serial.println("📡 Pinging all detected servos:");
    for (int id = 1; id <= MAX_SERVOS; id++) {
      if (servoManager.isServoDetected(id)) {
        bool success = servoManager.pingServo(id);
        Serial.printf("  Servo %d: %s\n", id, success ? "✅ OK" : "❌ No response");
      }
    }
  } else {
    // Ping specific servo
    int id = args.toInt();
    if (id >= 1 && id <= MAX_SERVOS) {
      bool success = servoManager.pingServo(id);
      Serial.printf("📡 Servo %d: %s\n", id, success ? "✅ OK" : "❌ No response");
    } else {
      Serial.println("❌ Invalid servo ID (1-16)");
    }
  }
}

void CommandHandler::cmdEnable(const String& args) {
  int space_pos = args.indexOf(' ');

  if (space_pos == -1) {
    Serial.println("❌ Usage: e [servo_id] [0/1]");
    return;
  }

  int id = args.substring(0, space_pos).toInt();
  int enable = args.substring(space_pos + 1).toInt();

  if (id >= 1 && id <= MAX_SERVOS && (enable == 0 || enable == 1)) {
    bool success = servoManager.enableTorque(id, enable == 1);
    Serial.printf("💪 Servo %d torque %s: %s\n",
                 id, enable ? "enable" : "disable", success ? "✅ OK" : "❌ Failed");
  } else {
    Serial.println("❌ Invalid parameters");
  }
}

void CommandHandler::cmdMove(const String& args) {
  // Parse: id position [time]
  int space1 = args.indexOf(' ');
  if (space1 == -1) {
    Serial.println("❌ Usage: m [servo_id] [position] [time_ms]");
    return;
  }

  int id = args.substring(0, space1).toInt();
  String remaining = args.substring(space1 + 1);

  int space2 = remaining.indexOf(' ');
  uint16_t position = remaining.substring(0, space2 == -1 ? remaining.length() : space2).toInt();
  uint16_t time_ms = space2 == -1 ? SERVO_DEFAULT_TIME : remaining.substring(space2 + 1).toInt();

  if (id >= 1 && id <= MAX_SERVOS && ServoManager::isValidPosition(position)) {
    bool success = servoManager.moveServo(id, position, time_ms);
    Serial.printf("🎯 Moving servo %d to %d: %s\n", id, position, success ? "✅ OK" : "❌ Failed");
  } else {
    Serial.println("❌ Invalid parameters");
  }
}

void CommandHandler::cmdRead(const String& args) {
  if (args.length() == 0) {
    // Read all detected servos
    Serial.println("📍 Reading all servo positions:");
    servoManager.updateAllPositions();
  } else {
    // Read specific servo
    int id = args.toInt();
    if (id >= 1 && id <= MAX_SERVOS) {
      int position = servoManager.readPosition(id);
      if (position >= 0) {
        Serial.printf("📍 Servo %d position: %d\n", id, position);
      } else {
        Serial.printf("❌ Failed to read servo %d position\n", id);
      }
    } else {
      Serial.println("❌ Invalid servo ID (1-16)");
    }
  }
}

void CommandHandler::cmdCenter(const String& args) {
  Serial.println("🎯 Centering all servos...");
  bool success = servoManager.centerAllServos();
  Serial.printf("Result: %s\n", success ? "✅ OK" : "❌ Some servos failed");
}

void CommandHandler::cmdStatus(const String& args) {
  servoManager.printServoStatus();
}

void CommandHandler::cmdTest(const String& args) {
  cmdHandler.setMode(MODE_TESTING);
  Serial.println("🧪 Running comprehensive test...");

  // Test sequence similar to previous implementation but using new system
  int found = servoManager.scanServos();
  if (found > 0) {
    servoManager.enableAllTorque(true);
    delay(1000);

    // Test movement on first detected servo
    for (int id = 1; id <= MAX_SERVOS; id++) {
      if (servoManager.isServoDetected(id)) {
        Serial.printf("🎯 Testing movement on servo %d\n", id);

        int initial_pos = servoManager.readPosition(id);
        servoManager.moveServo(id, 2048, 1000);
        delay(2000);

        int final_pos = servoManager.readPosition(id);

        if (initial_pos >= 0 && final_pos >= 0) {
          int error = abs(final_pos - 2048);
          Serial.printf("📊 Position test: %d → %d (error: %d)\n", initial_pos, final_pos, error);
          if (error < 100) {
            Serial.println("✅ Movement test passed");
          } else {
            Serial.println("⚠️ Large position error");
          }
        }
        break; // Test only first servo
      }
    }
  }

  cmdHandler.setMode(MODE_AUTONOMOUS);
}

void CommandHandler::cmdDance(const String& args) {
  String dance_type = args;
  dance_type.trim();
  dance_type.toLowerCase();

  DanceStep* steps;
  int step_count;

  if (dance_type == "extreme") {
    steps = extremeDanceSteps;
    step_count = 6; // EXTREME_DANCE_STEPS
  } else if (dance_type == "coordinated") {
    steps = coordinatedDanceSteps;
    step_count = 6; // COORDINATED_DANCE_STEPS
  } else {
    steps = basicDanceSteps;
    step_count = 4; // BASIC_DANCE_STEPS
  }

  servoManager.loadDanceSequence(steps, step_count, true);
  servoManager.startDance();
  cmdHandler.setMode(MODE_DANCING);

  Serial.printf("🕺 Started %s dance sequence (%d steps)\n",
               dance_type.length() > 0 ? dance_type.c_str() : "basic", step_count);
}

void CommandHandler::cmdStop(const String& args) {
  servoManager.stopDance();
  cmdHandler.setMode(MODE_AUTONOMOUS);
  Serial.println("⏹️ Stopped current action");
}

void CommandHandler::cmdConfig(const String& args) {
  Serial.println("\n⚙️ CONFIGURATION");
  Serial.println("================");
  Serial.printf("LED Pin: %d\n", LED_PIN);
  Serial.printf("Servo UART: RX=%d, TX=%d, Baud=%d\n", SERVO_UART_RX, SERVO_UART_TX, SERVO_UART_BAUD);
  Serial.printf("USB Baud: %d\n", USB_UART_BAUD);
  Serial.printf("Max Servos: %d\n", MAX_SERVOS);
  Serial.printf("Servo Range: %d-%d\n", SERVO_MIN_POSITION, SERVO_MAX_POSITION);
  Serial.printf("Default Speed: %d\n", SERVO_DEFAULT_SPEED);
  Serial.printf("Default Time: %d ms\n", SERVO_DEFAULT_TIME);
}

void CommandHandler::cmdDebug(const String& args) {
  // This would toggle debug flags - implementation depends on specific debug system
  Serial.printf("🔧 Debug toggle for: %s (not implemented)\n", args.c_str());
}