#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include "STS3032.h"

// Function prototypes
void initIMU();
void readIMU();
void discoverServos();
void updateServoPositions();
void processCommand(String command, Stream& output);
void showStatus(Stream& output);
void centerAllServos(Stream& output);
void startWalking(int steps, Stream& output);
void performWalkStep();
void stopWalking(Stream& output);
void sendPositionUpdate();
void showRealTimeMonitor(Stream& output);
void enterCalibrationMode(Stream& output);
void parseAndMove(String command, Stream& output);
void enableJsonMode(Stream& output);
void showIMUData(Stream& output);
void showBalanceStatus(Stream& output);

// MPU6050 (GY-521) registers
#define MPU6050_ADDR         0x68
#define MPU6050_PWR_MGMT_1   0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B
#define MPU6050_GYRO_XOUT_H  0x43

struct IMUData {
    float accelX, accelY, accelZ;
    float gyroX, gyroY, gyroZ;
    float pitch, roll, yaw;
    float temperature;
    bool isConnected;
};

// Hardware configuration for ESP32-S3
#define SERVO_SERIAL    Serial1  // Hardware Serial 1 (GPIO 17, 18)
#define SERVO_DIR_PIN   4        // Direction control pin for half-duplex
#define USB_SERIAL      Serial   // USB Serial for commands
#define LED_PIN         2        // Built-in LED

// IMU GY-521 (MPU6050) configuration
#define IMU_SDA_PIN     8        // I2C Data
#define IMU_SCL_PIN     9        // I2C Clock

// Servo controller and leg controller
STS3032 servoController;
PhoneWalkerLegs legs(&servoController);

// Servo mapping and calibration
struct ServoInfo {
    uint8_t id;
    String name;
    int16_t currentPosition;
    int16_t calibratedCenter;
    int16_t minPosition;
    int16_t maxPosition;
    bool isResponding;
    unsigned long lastUpdate;
};

ServoInfo detectedServos[16];
int servoCount = 0;
bool calibrationMode = false;
bool walkingActive = false;

// IMU data
IMUData imuData;

// JSON for communication
JsonDocument jsonDoc;

void setup() {
    // Initialize LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);

    // Initialize USB serial
    USB_SERIAL.begin(115200);
    delay(2000);

    USB_SERIAL.println("🤖 PhoneWalker ESP32-S3 Controller v2.0");
    USB_SERIAL.println("=========================================");
    USB_SERIAL.println("Features:");
    USB_SERIAL.println("- Real-time servo position monitoring");
    USB_SERIAL.println("- Servo calibration and enumeration");
    USB_SERIAL.println("- Walking simulation with feedback");

    // Initialize I2C for IMU (GY-521 on pins 8,9)
    USB_SERIAL.println("\n🔧 Initializing IMU (GY-521)...");
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
    Wire.setClock(400000);  // 400kHz I2C speed
    initIMU();

    // Initialize servo communication (proven working protocol)
    USB_SERIAL.println("\n🔧 Initializing servo communication...");
    SERVO_SERIAL.begin(1000000, SERIAL_8N1, 17, 18);  // TX=17, RX=18 for ESP32-S3
    servoController.begin(SERVO_SERIAL, SERVO_DIR_PIN);

    delay(1000);

    // Auto-discover and enumerate servos
    discoverServos();

    // Initialize leg controller with discovered servos
    if (servoCount >= 4) {
        legs.init(detectedServos[0].id, detectedServos[1].id,
                  detectedServos[2].id, detectedServos[3].id);
        USB_SERIAL.println("✅ PhoneWalker ready with " + String(servoCount) + " servos!");
    } else {
        USB_SERIAL.println("⚠️ Need at least 4 servos for walking, but can test with " + String(servoCount));
    }

    USB_SERIAL.println("\n📋 Commands:");
    USB_SERIAL.println("  scan         - Discover servos");
    USB_SERIAL.println("  status       - Show servo status");
    USB_SERIAL.println("  calibrate    - Enter calibration mode");
    USB_SERIAL.println("  center       - Move all servos to center");
    USB_SERIAL.println("  walk <steps> - Simulate walking");
    USB_SERIAL.println("  monitor      - Real-time position monitoring");
    USB_SERIAL.println("  imu          - Show IMU data");
    USB_SERIAL.println("  balance      - Show balance status");
    USB_SERIAL.println("  json         - JSON API mode");
    USB_SERIAL.println("\nReady for commands:");

    digitalWrite(LED_PIN, LOW);  // Ready indicator
}

void loop() {
    // Handle USB commands
    if (USB_SERIAL.available()) {
        String command = USB_SERIAL.readStringUntil('\n');
        command.trim();
        processCommand(command, USB_SERIAL);
    }

    // Real-time position monitoring
    static unsigned long lastMonitor = 0;
    if (millis() - lastMonitor > 500) {  // Monitor every 500ms
        updateServoPositions();
        lastMonitor = millis();
    }

    // Real-time IMU monitoring
    static unsigned long lastIMU = 0;
    if (millis() - lastIMU > 100) {  // Read IMU every 100ms
        readIMU();
        lastIMU = millis();
    }

    // Walking simulation
    if (walkingActive) {
        static unsigned long lastWalkStep = 0;
        if (millis() - lastWalkStep > 2000) {  // Step every 2 seconds
            performWalkStep();
            lastWalkStep = millis();
        }
    }

    // LED status indicator
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
        digitalWrite(LED_PIN, !digitalRead(LED_PIN));
        lastBlink = millis();
    }

    // Live status updates every 5 seconds
    static unsigned long lastStatus = 0;
    if (millis() - lastStatus > 5000) {
        USB_SERIAL.printf("[%lu] PhoneWalker alive - %d servos, IMU:%s, Free heap: %d\n",
                         millis(), servoCount, imuData.isConnected ? "OK" : "ERR", ESP.getFreeHeap());
        lastStatus = millis();
    }

    delay(10);
}

void discoverServos() {
    USB_SERIAL.println("🔍 Discovering servos (IDs 1-15)...");
    servoCount = 0;

    for (uint8_t id = 1; id <= 15; id++) {
        USB_SERIAL.print("Testing ID " + String(id) + "... ");

        if (servoController.ping(id)) {
            detectedServos[servoCount].id = id;
            detectedServos[servoCount].name = "Servo_" + String(id);
            detectedServos[servoCount].isResponding = true;
            detectedServos[servoCount].calibratedCenter = 2048;  // Default center
            detectedServos[servoCount].minPosition = 0;
            detectedServos[servoCount].maxPosition = 4095;
            detectedServos[servoCount].lastUpdate = millis();

            // Read initial position
            int16_t pos = servoController.getPosition(id);
            detectedServos[servoCount].currentPosition = (pos >= 0) ? pos : 2048;

            USB_SERIAL.println("FOUND ✅ (Position: " + String(detectedServos[servoCount].currentPosition) + ")");
            servoCount++;
        } else {
            USB_SERIAL.println("❌");
        }
        delay(100);
    }

    USB_SERIAL.println("\n📊 Discovery Summary:");
    USB_SERIAL.println("Found " + String(servoCount) + " servos:");
    for (int i = 0; i < servoCount; i++) {
        USB_SERIAL.println("  " + detectedServos[i].name + " (ID: " + String(detectedServos[i].id) +
                          ") - Position: " + String(detectedServos[i].currentPosition));
    }
}

void updateServoPositions() {
    for (int i = 0; i < servoCount; i++) {
        int16_t pos = servoController.getPosition(detectedServos[i].id);
        if (pos >= 0) {
            detectedServos[i].currentPosition = pos;
            detectedServos[i].lastUpdate = millis();
            detectedServos[i].isResponding = true;
        } else {
            detectedServos[i].isResponding = false;
        }
    }
}

void processCommand(String command, Stream& output) {
    command.toLowerCase();

    if (command == "scan") {
        discoverServos();
    }
    else if (command == "status") {
        showStatus(output);
    }
    else if (command == "calibrate") {
        enterCalibrationMode(output);
    }
    else if (command == "center") {
        centerAllServos(output);
    }
    else if (command.startsWith("walk ")) {
        int steps = command.substring(5).toInt();
        startWalking(steps, output);
    }
    else if (command == "stop") {
        stopWalking(output);
    }
    else if (command == "monitor") {
        showRealTimeMonitor(output);
    }
    else if (command == "imu") {
        showIMUData(output);
    }
    else if (command == "balance") {
        showBalanceStatus(output);
    }
    else if (command == "json") {
        enableJsonMode(output);
    }
    else if (command.startsWith("move ")) {
        parseAndMove(command, output);
    }
    else {
        output.println("Unknown command: " + command);
        output.println("Type 'status' for current state or try: scan, center, imu");
    }
}

void showStatus(Stream& output) {
    output.println("\n📊 PhoneWalker Status");
    output.println("===================");
    output.println("ESP32-S3 Controller: ✅ Online");
    output.println("Servos Found: " + String(servoCount));
    output.println("Walking: " + String(walkingActive ? "Active" : "Stopped"));
    output.println("IMU Status: " + String(imuData.isConnected ? "✅ Connected" : "❌ Disconnected"));
    output.printf("Free Heap: %d bytes\n", ESP.getFreeHeap());
    output.println("");

    output.println("📍 Servo Positions:");
    output.println("ID | Name     | Position | Status | Last Update");
    output.println("---|----------|----------|--------|------------");

    for (int i = 0; i < servoCount; i++) {
        String status = detectedServos[i].isResponding ? "✅ OK" : "❌ ERR";
        unsigned long timeSince = millis() - detectedServos[i].lastUpdate;

        output.printf("%2d | %-8s | %8d | %6s | %6lums\n",
                     detectedServos[i].id,
                     detectedServos[i].name.c_str(),
                     detectedServos[i].currentPosition,
                     status.c_str(),
                     timeSince);
    }
}

void centerAllServos(Stream& output) {
    if (servoCount == 0) {
        output.println("❌ No servos found. Run 'scan' first.");
        return;
    }

    output.println("🎯 Centering all servos...");

    for (int i = 0; i < servoCount; i++) {
        output.println("Centering " + detectedServos[i].name + " (ID: " + String(detectedServos[i].id) + ")");

        servoController.setTorqueEnable(detectedServos[i].id, true);
        delay(100);

        servoController.setPosition(detectedServos[i].id, detectedServos[i].calibratedCenter, 1000);
        delay(200);
    }

    output.println("✅ All servos centered!");
}

void startWalking(int steps, Stream& output) {
    if (servoCount < 2) {
        output.println("❌ Need at least 2 servos for walking demo");
        return;
    }

    output.println("🚶 Starting walking simulation (" + String(steps) + " steps)");
    walkingActive = true;

    // Enable torque on available servos
    for (int i = 0; i < min(4, servoCount); i++) {
        servoController.setTorqueEnable(detectedServos[i].id, true);
    }

    // Start with centered position
    centerAllServos(output);
}

void performWalkStep() {
    static int walkPhase = 0;
    static int currentStep = 0;

    if (!walkingActive || servoCount < 2) return;

    USB_SERIAL.println("🦶 Walk phase " + String(walkPhase) + ", step " + String(currentStep));

    // Simple walking gait adapted for available servos
    if (servoCount >= 4) {
        // Full 4-servo walking
        switch (walkPhase) {
            case 0: // Lift front legs
                servoController.setPosition(detectedServos[0].id, detectedServos[0].calibratedCenter - 200, 500);
                servoController.setPosition(detectedServos[1].id, detectedServos[1].calibratedCenter - 200, 500);
                break;
            case 1: // Move front legs forward, back legs back
                servoController.setPosition(detectedServos[0].id, detectedServos[0].calibratedCenter - 100, 500);
                servoController.setPosition(detectedServos[1].id, detectedServos[1].calibratedCenter - 100, 500);
                servoController.setPosition(detectedServos[2].id, detectedServos[2].calibratedCenter + 100, 500);
                servoController.setPosition(detectedServos[3].id, detectedServos[3].calibratedCenter + 100, 500);
                break;
            case 2: // Lower front legs, lift back legs
                servoController.setPosition(detectedServos[0].id, detectedServos[0].calibratedCenter, 500);
                servoController.setPosition(detectedServos[1].id, detectedServos[1].calibratedCenter, 500);
                servoController.setPosition(detectedServos[2].id, detectedServos[2].calibratedCenter - 200, 500);
                servoController.setPosition(detectedServos[3].id, detectedServos[3].calibratedCenter - 200, 500);
                break;
            case 3: // Move back legs forward, front legs back
                servoController.setPosition(detectedServos[0].id, detectedServos[0].calibratedCenter + 100, 500);
                servoController.setPosition(detectedServos[1].id, detectedServos[1].calibratedCenter + 100, 500);
                servoController.setPosition(detectedServos[2].id, detectedServos[2].calibratedCenter - 100, 500);
                servoController.setPosition(detectedServos[3].id, detectedServos[3].calibratedCenter - 100, 500);
                break;
        }
    } else {
        // Simple alternating motion for 1-2 servos
        int offset = (walkPhase % 2 == 0) ? -300 : 300;
        for (int i = 0; i < servoCount; i++) {
            int servoOffset = (i % 2 == 0) ? offset : -offset;
            servoController.setPosition(detectedServos[i].id, detectedServos[i].calibratedCenter + servoOffset, 500);
        }
    }

    walkPhase = (walkPhase + 1) % 4;
    if (walkPhase == 0) currentStep++;

    // Send real-time position data
    sendPositionUpdate();
}

void stopWalking(Stream& output) {
    walkingActive = false;
    output.println("🛑 Walking stopped");
    centerAllServos(output);
}

void sendPositionUpdate() {
    // Send JSON position update
    jsonDoc.clear();
    jsonDoc["type"] = "position_update";
    jsonDoc["timestamp"] = millis();

    JsonArray servos = jsonDoc["servos"].to<JsonArray>();
    for (int i = 0; i < servoCount; i++) {
        JsonObject servo = servos.add<JsonObject>();
        servo["id"] = detectedServos[i].id;
        servo["name"] = detectedServos[i].name;
        servo["position"] = detectedServos[i].currentPosition;
        servo["responding"] = detectedServos[i].isResponding;
    }

    // Add IMU data
    JsonObject imu = jsonDoc["imu"].to<JsonObject>();
    imu["connected"] = imuData.isConnected;
    imu["pitch"] = imuData.pitch;
    imu["roll"] = imuData.roll;
    imu["accel_x"] = imuData.accelX;
    imu["accel_y"] = imuData.accelY;
    imu["accel_z"] = imuData.accelZ;

    String jsonString;
    serializeJson(jsonDoc, jsonString);
    USB_SERIAL.println("JSON: " + jsonString);
}

void showRealTimeMonitor(Stream& output) {
    output.println("📡 Real-time servo monitoring (10 seconds)...");

    unsigned long startTime = millis();
    while (millis() - startTime < 10000) {
        updateServoPositions();

        output.print("[" + String(millis()) + "] Positions: ");
        for (int i = 0; i < servoCount && i < 4; i++) {
            output.print("S" + String(detectedServos[i].id) + ":" + String(detectedServos[i].currentPosition) + " ");
        }
        if (imuData.isConnected) {
            output.printf("IMU: P=%.1f° R=%.1f°", imuData.pitch, imuData.roll);
        }
        output.println();

        delay(500);
    }
}

void enterCalibrationMode(Stream& output) {
    output.println("🎛️ Entering calibration mode...");
    output.println("Commands: 'cal <id> <position>' or 'done' to exit");
    calibrationMode = true;
    // Implementation for calibration commands...
}

void parseAndMove(String command, Stream& output) {
    // Parse: move <id> <position> [time]
    int firstSpace = command.indexOf(' ', 5);
    int secondSpace = command.indexOf(' ', firstSpace + 1);

    if (firstSpace == -1) {
        output.println("Usage: move <id> <position> [time]");
        return;
    }

    int id = command.substring(5, firstSpace).toInt();
    int position = command.substring(firstSpace + 1, (secondSpace > 0) ? secondSpace : command.length()).toInt();
    int time_ms = (secondSpace > 0) ? command.substring(secondSpace + 1).toInt() : 1000;

    output.println("Moving servo " + String(id) + " to " + String(position) + " (time: " + String(time_ms) + "ms)");

    servoController.setTorqueEnable(id, true);
    servoController.setPosition(id, position, time_ms);
}

void enableJsonMode(Stream& output) {
    output.println("📋 JSON API Mode enabled");
    output.println("Live data streaming...");
    sendPositionUpdate();
}

// IMU Functions
void initIMU() {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_PWR_MGMT_1);
    Wire.write(0);  // Wake up the MPU6050
    if (Wire.endTransmission() == 0) {
        imuData.isConnected = true;
        USB_SERIAL.println("✅ GY-521 (MPU6050) initialized successfully");
    } else {
        imuData.isConnected = false;
        USB_SERIAL.println("❌ GY-521 (MPU6050) not found on I2C");
    }
}

void readIMU() {
    if (!imuData.isConnected) return;

    // Read accelerometer and gyroscope data
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_ACCEL_XOUT_H);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU6050_ADDR, (uint8_t)14, (uint8_t)1);

    if (Wire.available() >= 14) {
        // Read accelerometer
        int16_t accelX = (Wire.read() << 8) | Wire.read();
        int16_t accelY = (Wire.read() << 8) | Wire.read();
        int16_t accelZ = (Wire.read() << 8) | Wire.read();

        // Read temperature
        int16_t temperature = (Wire.read() << 8) | Wire.read();

        // Read gyroscope
        int16_t gyroX = (Wire.read() << 8) | Wire.read();
        int16_t gyroY = (Wire.read() << 8) | Wire.read();
        int16_t gyroZ = (Wire.read() << 8) | Wire.read();

        // Convert to meaningful units
        imuData.accelX = accelX / 16384.0;  // ±2g range
        imuData.accelY = accelY / 16384.0;
        imuData.accelZ = accelZ / 16384.0;

        imuData.gyroX = gyroX / 131.0;  // ±250°/s range
        imuData.gyroY = gyroY / 131.0;
        imuData.gyroZ = gyroZ / 131.0;

        imuData.temperature = temperature / 340.0 + 36.53;

        // Calculate pitch and roll
        imuData.roll = atan2(imuData.accelY, imuData.accelZ) * 180.0 / PI;
        imuData.pitch = atan2(-imuData.accelX, sqrt(imuData.accelY * imuData.accelY + imuData.accelZ * imuData.accelZ)) * 180.0 / PI;
    }
}

void showIMUData(Stream& output) {
    if (!imuData.isConnected) {
        output.println("❌ IMU not connected");
        return;
    }

    output.println("\n🧭 IMU Data (GY-521 MPU6050)");
    output.println("============================");
    output.printf("Accelerometer (g): X=%.3f, Y=%.3f, Z=%.3f\n",
                  imuData.accelX, imuData.accelY, imuData.accelZ);
    output.printf("Gyroscope (°/s):   X=%.2f, Y=%.2f, Z=%.2f\n",
                  imuData.gyroX, imuData.gyroY, imuData.gyroZ);
    output.printf("Orientation:       Pitch=%.1f°, Roll=%.1f°\n",
                  imuData.pitch, imuData.roll);
    output.printf("Temperature:       %.1f°C\n", imuData.temperature);
}

void showBalanceStatus(Stream& output) {
    if (!imuData.isConnected) {
        output.println("❌ IMU not connected - cannot check balance");
        return;
    }

    output.println("\n⚖️ Balance Status");
    output.println("================");

    // Determine balance state
    bool isUpright = (abs(imuData.pitch) < 45 && abs(imuData.roll) < 45);
    bool isStable = (abs(imuData.gyroX) < 50 && abs(imuData.gyroY) < 50 && abs(imuData.gyroZ) < 50);

    output.printf("Upright:    %s (Pitch: %.1f°, Roll: %.1f°)\n",
                  isUpright ? "✅ YES" : "❌ NO", imuData.pitch, imuData.roll);
    output.printf("Stable:     %s (GyroX: %.1f°/s, GyroY: %.1f°/s)\n",
                  isStable ? "✅ YES" : "❌ NO", imuData.gyroX, imuData.gyroY);

    if (!isUpright) {
        output.println("⚠️ WARNING: Robot may have fallen!");
    }
    if (!isStable) {
        output.println("⚠️ WARNING: Robot is moving/shaking!");
    }
    if (isUpright && isStable) {
        output.println("✅ Robot is balanced and stable");
    }
}