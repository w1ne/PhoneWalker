#include <Arduino.h>
#include "STS3032.h"

// Hardware configuration
#define SERVO_SERIAL    Serial2  // ESP32 Hardware Serial 2 (pins 16, 17)
#define SERVO_DIR_PIN   4        // Direction control pin for half-duplex communication
#define USB_SERIAL      Serial   // USB Serial for commands

// Servo controller and leg controller
STS3032 servoController;
PhoneWalkerLegs legs(&servoController);

// Servo IDs for the 4-legged walker (using first 4 of your 15 servos)
const uint8_t FRONT_LEFT_ID = 1;
const uint8_t FRONT_RIGHT_ID = 2;
const uint8_t BACK_LEFT_ID = 3;
const uint8_t BACK_RIGHT_ID = 4;

// Command parsing variables
String inputString = "";
bool stringComplete = false;

void setup() {
    // Initialize USB serial for commands
    USB_SERIAL.begin(115200);
    while (!USB_SERIAL && millis() < 3000) {
        delay(10);
    }

    USB_SERIAL.println("PhoneWalker Servo Controller v1.0");
    USB_SERIAL.println("==================================");

    // Initialize servo serial communication
    SERVO_SERIAL.begin(1000000);  // 1Mbps - standard for STS3032
    servoController.begin(SERVO_SERIAL, SERVO_DIR_PIN);

    // Initialize leg controller
    legs.init(FRONT_LEFT_ID, FRONT_RIGHT_ID, BACK_LEFT_ID, BACK_RIGHT_ID);
    legs.setNeutralPosition(2048);  // Center position
    legs.setGaitParameters(200, 150);  // Lift height and step length

    delay(1000);

    // Scan for connected servos
    USB_SERIAL.println("Scanning for servos...");
    uint8_t foundServos[16];
    bool found = servoController.scanServos(foundServos, 16);

    if (found) {
        USB_SERIAL.print("Found servos with IDs: ");
        for (int i = 0; i < 16; i++) {
            if (foundServos[i] != 0) {
                USB_SERIAL.print(foundServos[i]);
                USB_SERIAL.print(" ");
            }
        }
        USB_SERIAL.println();
    } else {
        USB_SERIAL.println("No servos found! Check connections and power.");
    }

    USB_SERIAL.println("\nCommands:");
    USB_SERIAL.println("  scan - Scan for servos");
    USB_SERIAL.println("  ping <id> - Ping servo");
    USB_SERIAL.println("  pos <id> <position> [time] [speed] - Set servo position");
    USB_SERIAL.println("  get <id> - Get servo position");
    USB_SERIAL.println("  enable <id> - Enable servo torque");
    USB_SERIAL.println("  disable <id> - Disable servo torque");
    USB_SERIAL.println("  standup - Stand up robot");
    USB_SERIAL.println("  sitdown - Sit down robot");
    USB_SERIAL.println("  walk <steps> - Walk forward");
    USB_SERIAL.println("  stop - Stop all movement");
    USB_SERIAL.println("  test - Test individual servo movements");
    USB_SERIAL.println("  status - Get servo status");
    USB_SERIAL.println();
    USB_SERIAL.println("Ready for commands:");
}

void loop() {
    // Handle serial input
    while (USB_SERIAL.available()) {
        char inChar = (char)USB_SERIAL.read();
        inputString += inChar;

        if (inChar == '\n') {
            stringComplete = true;
        }
    }

    // Process complete commands
    if (stringComplete) {
        inputString.trim();
        processCommand(inputString);
        inputString = "";
        stringComplete = false;
        USB_SERIAL.println("\nReady for commands:");
    }

    delay(10);
}

void processCommand(String command) {
    command.toLowerCase();

    if (command.startsWith("scan")) {
        scanServos();
    }
    else if (command.startsWith("ping ")) {
        int id = command.substring(5).toInt();
        pingServo(id);
    }
    else if (command.startsWith("pos ")) {
        parsePositionCommand(command);
    }
    else if (command.startsWith("get ")) {
        int id = command.substring(4).toInt();
        getServoPosition(id);
    }
    else if (command.startsWith("enable ")) {
        int id = command.substring(7).toInt();
        enableServo(id, true);
    }
    else if (command.startsWith("disable ")) {
        int id = command.substring(8).toInt();
        enableServo(id, false);
    }
    else if (command == "standup") {
        standUp();
    }
    else if (command == "sitdown") {
        sitDown();
    }
    else if (command.startsWith("walk ")) {
        int steps = command.substring(5).toInt();
        walkForward(steps);
    }
    else if (command == "stop") {
        stopMovement();
    }
    else if (command == "test") {
        testServos();
    }
    else if (command == "status") {
        showServoStatus();
    }
    else if (command == "help") {
        showHelp();
    }
    else {
        USB_SERIAL.println("Unknown command. Type 'help' for available commands.");
    }
}

void scanServos() {
    USB_SERIAL.println("Scanning for servos...");
    uint8_t foundServos[16];
    memset(foundServos, 0, sizeof(foundServos));

    int count = 0;
    for (uint8_t id = 1; id <= 15; id++) {
        USB_SERIAL.print("Checking ID ");
        USB_SERIAL.print(id);
        USB_SERIAL.print("... ");

        if (servoController.ping(id)) {
            foundServos[count++] = id;
            USB_SERIAL.println("Found!");
        } else {
            USB_SERIAL.println("Not found");
        }
        delay(50);
    }

    if (count > 0) {
        USB_SERIAL.print("\nFound ");
        USB_SERIAL.print(count);
        USB_SERIAL.print(" servos: ");
        for (int i = 0; i < count; i++) {
            USB_SERIAL.print(foundServos[i]);
            if (i < count - 1) USB_SERIAL.print(", ");
        }
        USB_SERIAL.println();
    } else {
        USB_SERIAL.println("\nNo servos found!");
    }
}

void pingServo(int id) {
    USB_SERIAL.print("Pinging servo ID ");
    USB_SERIAL.print(id);
    USB_SERIAL.print("... ");

    if (servoController.ping(id)) {
        USB_SERIAL.println("Response OK!");
    } else {
        USB_SERIAL.println("No response");
    }
}

void parsePositionCommand(String command) {
    // Parse: pos <id> <position> [time] [speed]
    int firstSpace = command.indexOf(' ', 4);
    int secondSpace = command.indexOf(' ', firstSpace + 1);
    int thirdSpace = command.indexOf(' ', secondSpace + 1);

    if (firstSpace == -1 || secondSpace == -1) {
        USB_SERIAL.println("Usage: pos <id> <position> [time] [speed]");
        return;
    }

    int id = command.substring(4, firstSpace).toInt();
    int position = command.substring(firstSpace + 1, secondSpace).toInt();
    int time = 500;  // Default time
    int speed = 0;   // Default speed

    if (thirdSpace != -1) {
        time = command.substring(secondSpace + 1, thirdSpace).toInt();
        speed = command.substring(thirdSpace + 1).toInt();
    } else if (secondSpace != -1) {
        String remaining = command.substring(secondSpace + 1);
        if (remaining.length() > 0) {
            time = remaining.toInt();
        }
    }

    USB_SERIAL.print("Moving servo ");
    USB_SERIAL.print(id);
    USB_SERIAL.print(" to position ");
    USB_SERIAL.print(position);
    USB_SERIAL.print(" (time: ");
    USB_SERIAL.print(time);
    USB_SERIAL.print("ms, speed: ");
    USB_SERIAL.print(speed);
    USB_SERIAL.println(")");

    if (servoController.setPosition(id, position, time, speed)) {
        USB_SERIAL.println("Command sent successfully");
    } else {
        USB_SERIAL.println("Failed to send command");
    }
}

void getServoPosition(int id) {
    USB_SERIAL.print("Reading position from servo ");
    USB_SERIAL.print(id);
    USB_SERIAL.print("... ");

    int16_t position = servoController.getPosition(id);
    if (position >= 0) {
        USB_SERIAL.print("Position: ");
        USB_SERIAL.println(position);
    } else {
        USB_SERIAL.println("Failed to read position");
    }
}

void enableServo(int id, bool enable) {
    USB_SERIAL.print(enable ? "Enabling" : "Disabling");
    USB_SERIAL.print(" torque for servo ");
    USB_SERIAL.print(id);
    USB_SERIAL.print("... ");

    if (servoController.setTorqueEnable(id, enable)) {
        USB_SERIAL.println("Success");
    } else {
        USB_SERIAL.println("Failed");
    }
}

void standUp() {
    USB_SERIAL.println("Standing up...");
    if (legs.standUp()) {
        USB_SERIAL.println("Robot standing up!");
    } else {
        USB_SERIAL.println("Failed to stand up");
    }
}

void sitDown() {
    USB_SERIAL.println("Sitting down...");
    if (legs.sitDown()) {
        USB_SERIAL.println("Robot sitting down!");
    } else {
        USB_SERIAL.println("Failed to sit down");
    }
}

void walkForward(int steps) {
    USB_SERIAL.print("Walking forward ");
    USB_SERIAL.print(steps);
    USB_SERIAL.println(" steps...");

    if (legs.walkForward(steps)) {
        USB_SERIAL.println("Walk complete!");
    } else {
        USB_SERIAL.println("Walk failed");
    }
}

void stopMovement() {
    USB_SERIAL.println("Stopping all movement...");
    if (legs.stop()) {
        USB_SERIAL.println("All servos stopped");
    } else {
        USB_SERIAL.println("Failed to stop");
    }
}

void testServos() {
    USB_SERIAL.println("Testing servo movements...");

    // Test each of the main 4 servos
    uint8_t testServos[] = {FRONT_LEFT_ID, FRONT_RIGHT_ID, BACK_LEFT_ID, BACK_RIGHT_ID};
    String servoNames[] = {"Front Left", "Front Right", "Back Left", "Back Right"};

    for (int i = 0; i < 4; i++) {
        USB_SERIAL.print("Testing ");
        USB_SERIAL.print(servoNames[i]);
        USB_SERIAL.print(" (ID ");
        USB_SERIAL.print(testServos[i]);
        USB_SERIAL.println(")");

        // Enable servo
        servoController.setTorqueEnable(testServos[i], true);
        delay(100);

        // Move to center
        servoController.setPosition(testServos[i], 2048, 1000);
        delay(1200);

        // Move up
        servoController.setPosition(testServos[i], 1848, 500);  // +200
        delay(600);

        // Move down
        servoController.setPosition(testServos[i], 2248, 500);  // -200
        delay(600);

        // Return to center
        servoController.setPosition(testServos[i], 2048, 500);
        delay(600);

        USB_SERIAL.println("  Test complete");
    }

    USB_SERIAL.println("All servo tests complete!");
}

void showServoStatus() {
    USB_SERIAL.println("Servo Status:");
    USB_SERIAL.println("ID | Position | Speed | Load | Voltage | Temp | Moving");
    USB_SERIAL.println("---|----------|-------|------|---------|------|-------");

    uint8_t testServos[] = {FRONT_LEFT_ID, FRONT_RIGHT_ID, BACK_LEFT_ID, BACK_RIGHT_ID};

    for (int i = 0; i < 4; i++) {
        uint8_t id = testServos[i];
        int16_t pos = servoController.getPosition(id);
        int16_t speed = servoController.getSpeed(id);
        int16_t load = servoController.getLoad(id);
        uint8_t voltage = servoController.getVoltage(id);
        uint8_t temp = servoController.getTemperature(id);
        bool moving = servoController.isMoving(id);

        USB_SERIAL.print(" ");
        USB_SERIAL.print(id);
        USB_SERIAL.print(" | ");
        USB_SERIAL.print(pos >= 0 ? String(pos) : "ERR ");
        USB_SERIAL.print("    | ");
        USB_SERIAL.print(speed >= 0 ? String(speed) : "ERR");
        USB_SERIAL.print("   | ");
        USB_SERIAL.print(load >= 0 ? String(load) : "ERR");
        USB_SERIAL.print("  | ");
        USB_SERIAL.print(voltage > 0 ? String(voltage/10.0, 1) + "V" : "ERR ");
        USB_SERIAL.print("   | ");
        USB_SERIAL.print(temp > 0 ? String(temp) + "°C" : "ERR");
        USB_SERIAL.print(" | ");
        USB_SERIAL.println(moving ? "YES" : "NO ");

        delay(50);  // Small delay between queries
    }
}

void showHelp() {
    USB_SERIAL.println("\nPhoneWalker Servo Controller Commands:");
    USB_SERIAL.println("=====================================");
    USB_SERIAL.println("Basic servo control:");
    USB_SERIAL.println("  scan                     - Scan for connected servos");
    USB_SERIAL.println("  ping <id>                - Test communication with servo");
    USB_SERIAL.println("  pos <id> <pos> [t] [s]   - Set position (0-4095), time (ms), speed");
    USB_SERIAL.println("  get <id>                 - Get current servo position");
    USB_SERIAL.println("  enable <id>              - Enable servo torque");
    USB_SERIAL.println("  disable <id>             - Disable servo torque");
    USB_SERIAL.println("");
    USB_SERIAL.println("Walking robot control:");
    USB_SERIAL.println("  standup                  - Make robot stand up");
    USB_SERIAL.println("  sitdown                  - Make robot sit down");
    USB_SERIAL.println("  walk <steps>             - Walk forward N steps");
    USB_SERIAL.println("  stop                     - Stop all movement");
    USB_SERIAL.println("");
    USB_SERIAL.println("Testing and diagnostics:");
    USB_SERIAL.println("  test                     - Test all 4 leg servos");
    USB_SERIAL.println("  status                   - Show servo status");
    USB_SERIAL.println("  help                     - Show this help");
    USB_SERIAL.println("");
    USB_SERIAL.println("Examples:");
    USB_SERIAL.println("  pos 1 2048              - Move servo 1 to center position");
    USB_SERIAL.println("  pos 2 1500 1000 200     - Move servo 2 to 1500 in 1s at speed 200");
    USB_SERIAL.println("  walk 5                   - Walk forward 5 steps");
}