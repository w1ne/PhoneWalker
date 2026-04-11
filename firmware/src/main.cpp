#include <Arduino.h>
#include <WiFi.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>
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
void setRGBLED(uint8_t r, uint8_t g, uint8_t b);
void setLEDStatus(int status);

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

// Hardware configuration for Waveshare ESP32-S3-Zero
#define SERVO_SERIAL    Serial1  // Hardware Serial 1 (GPIO 17, 18)
#define USB_SERIAL      Serial   // USB Serial for commands
#define RGB_LED_PIN     21       // WS2812B RGB LED on GPIO21 (ESP32-S3-Zero)
#define LED_COUNT       1        // Single RGB LED
#define LED_BRIGHTNESS  50       // LED brightness (0-255)

// IMU GY-521 (MPU6050) configuration
#define IMU_SDA_PIN     8        // I2C Data
#define IMU_SCL_PIN     9        // I2C Clock

// LED Status Codes
#define LED_STARTUP     1
#define LED_SCANNING    2
#define LED_SERVO_FOUND 3
#define LED_IMU_OK      4
#define LED_IMU_ERROR   5
#define LED_READY       6
#define LED_WALKING     7
#define LED_ERROR       8

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

// NeoPixel RGB LED object
Adafruit_NeoPixel rgbLED(LED_COUNT, RGB_LED_PIN, NEO_GRB + NEO_KHZ800);

// RGB LED Control for WS2812B using NeoPixel library
void setRGBLED(uint8_t r, uint8_t g, uint8_t b) {
    rgbLED.setPixelColor(0, rgbLED.Color(r, g, b));
    rgbLED.show();
}

void setLEDStatus(int status) {
    switch(status) {
        case LED_STARTUP:
            setRGBLED(255, 255, 0);  // Yellow - starting up
            break;
        case LED_SCANNING:
            setRGBLED(0, 0, 255);    // Blue - scanning servos
            break;
        case LED_SERVO_FOUND:
            setRGBLED(0, 255, 0);    // Green - servo found
            delay(200);
            setRGBLED(0, 0, 0);      // Off
            delay(200);
            setRGBLED(0, 255, 0);    // Green again
            delay(200);
            setRGBLED(0, 0, 0);      // Off
            break;
        case LED_IMU_OK:
            setRGBLED(0, 255, 255);  // Cyan - IMU working
            break;
        case LED_IMU_ERROR:
            setRGBLED(255, 0, 0);    // Red - IMU error
            break;
        case LED_READY:
            setRGBLED(0, 255, 0);    // Green - ready
            break;
        case LED_WALKING:
            setRGBLED(255, 0, 255);  // Magenta - walking
            break;
        case LED_ERROR:
            setRGBLED(255, 0, 0);    // Red - error
            break;
        default:
            setRGBLED(0, 0, 0);      // Off
    }
}

void setup() {
    // Initialize RGB LED (NeoPixel)
    rgbLED.begin();
    rgbLED.setBrightness(LED_BRIGHTNESS);
    rgbLED.show(); // Turn off LED initially
    setLEDStatus(LED_STARTUP);

    // Initialize USB serial
    USB_SERIAL.begin(115200);
    delay(2000);

    USB_SERIAL.println("🤖 PhoneWalker ESP32-S3 Controller v2.0 (Waveshare RGB)");
    USB_SERIAL.println("=========================================================");
    USB_SERIAL.println("Features:");
    USB_SERIAL.println("- Real-time servo position monitoring");
    USB_SERIAL.println("- Servo calibration and enumeration");
    USB_SERIAL.println("- Walking simulation with feedback");
    USB_SERIAL.println("- RGB LED status indicators");

    // Initialize I2C for IMU (GY-521 on pins 8,9)
    USB_SERIAL.println("\n🔧 Initializing IMU (GY-521)...");
    Wire.begin(IMU_SDA_PIN, IMU_SCL_PIN);
    Wire.setClock(400000);  // 400kHz I2C speed
    initIMU();

    if (imuData.isConnected) {
        setLEDStatus(LED_IMU_OK);
        USB_SERIAL.println("✅ IMU initialized successfully");
        delay(1000);
    } else {
        setLEDStatus(LED_IMU_ERROR);
        USB_SERIAL.println("❌ IMU initialization failed");
        delay(2000);
    }

    // Initialize servo communication
    USB_SERIAL.println("\n🔧 Initializing servo communication...");
    SERVO_SERIAL.begin(1000000, SERIAL_8N1, 18, 17);  // RX=18, TX=17
    servoController.begin(SERVO_SERIAL);  // No direction control - Waveshare adapter handles it

    delay(1000);

    // Auto-discover and enumerate servos
    discoverServos();

    // Initialize leg controller with discovered servos
    if (servoCount >= 4) {
        legs.init(detectedServos[0].id, detectedServos[1].id,
                  detectedServos[2].id, detectedServos[3].id);
        USB_SERIAL.println("✅ PhoneWalker ready with " + String(servoCount) + " servos!");
    } else {
        USB_SERIAL.println("⚠️ Need at least 4 servos for walking, found " + String(servoCount));
    }

    USB_SERIAL.println("\n📋 Commands:");
    USB_SERIAL.println("  scan         - Discover servos");
    USB_SERIAL.println("  status       - Show servo status");
    USB_SERIAL.println("  center       - Move all servos to center");
    USB_SERIAL.println("  walk <steps> - Simulate walking");
    USB_SERIAL.println("  monitor      - Real-time position monitoring");
    USB_SERIAL.println("  imu          - Show IMU data");
    USB_SERIAL.println("  json         - JSON API mode");
    USB_SERIAL.println("\nReady for commands:");

    setLEDStatus(LED_READY);
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
    if (millis() - lastMonitor > 500) {
        updateServoPositions();
        lastMonitor = millis();
    }

    // Real-time IMU monitoring
    static unsigned long lastIMU = 0;
    if (millis() - lastIMU > 100) {
        readIMU();
        lastIMU = millis();
    }

    // Walking simulation
    if (walkingActive) {
        setLEDStatus(LED_WALKING);
        static unsigned long lastWalkStep = 0;
        if (millis() - lastWalkStep > 2000) {
            performWalkStep();
            lastWalkStep = millis();
        }
    } else if (!imuData.isConnected) {
        setLEDStatus(LED_IMU_ERROR);
    } else {
        setLEDStatus(LED_READY);
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
    setLEDStatus(LED_SCANNING);
    servoCount = 0;

    for (uint8_t id = 1; id <= 15; id++) {
        USB_SERIAL.print("Testing ID " + String(id) + "... ");

        if (servoController.ping(id)) {
            setLEDStatus(LED_SERVO_FOUND);
            detectedServos[servoCount].id = id;
            detectedServos[servoCount].name = "Servo_" + String(id);
            detectedServos[servoCount].isResponding = true;
            detectedServos[servoCount].calibratedCenter = 2048;
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

    setLEDStatus(LED_SCANNING);
    USB_SERIAL.println("\n📊 Discovery Summary:");
    USB_SERIAL.println("Found " + String(servoCount) + " servos:");
    for (int i = 0; i < servoCount; i++) {
        USB_SERIAL.println("  " + detectedServos[i].name + " (ID: " + String(detectedServos[i].id) +
                          ") - Position: " + String(detectedServos[i].currentPosition));
    }
}

void initIMU() {
    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_PWR_MGMT_1);
    Wire.write(0x00);  // Wake up MPU6050
    byte error = Wire.endTransmission();

    if (error == 0) {
        imuData.isConnected = true;
        USB_SERIAL.println("✅ MPU6050 initialized successfully");
    } else {
        imuData.isConnected = false;
        USB_SERIAL.printf("❌ MPU6050 initialization failed (error: %d)\n", error);
    }
}

void readIMU() {
    if (!imuData.isConnected) return;

    Wire.beginTransmission(MPU6050_ADDR);
    Wire.write(MPU6050_ACCEL_XOUT_H);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU6050_ADDR, 14, true);

    if (Wire.available() >= 14) {
        int16_t accelX = Wire.read() << 8 | Wire.read();
        int16_t accelY = Wire.read() << 8 | Wire.read();
        int16_t accelZ = Wire.read() << 8 | Wire.read();
        int16_t temp = Wire.read() << 8 | Wire.read();
        int16_t gyroX = Wire.read() << 8 | Wire.read();
        int16_t gyroY = Wire.read() << 8 | Wire.read();
        int16_t gyroZ = Wire.read() << 8 | Wire.read();

        // Convert to meaningful units
        imuData.accelX = accelX / 16384.0;  // ±2g range
        imuData.accelY = accelY / 16384.0;
        imuData.accelZ = accelZ / 16384.0;
        imuData.gyroX = gyroX / 131.0;      // ±250°/s range
        imuData.gyroY = gyroY / 131.0;
        imuData.gyroZ = gyroZ / 131.0;
        imuData.temperature = temp / 340.0 + 36.53;

        // Calculate pitch and roll
        imuData.pitch = atan2(imuData.accelY, sqrt(imuData.accelX * imuData.accelX + imuData.accelZ * imuData.accelZ)) * 180 / PI;
        imuData.roll = atan2(-imuData.accelX, imuData.accelZ) * 180 / PI;
    }
}

void processCommand(String command, Stream& output) {
    command.toLowerCase();

    if (command == "scan") {
        discoverServos();
    } else if (command == "status") {
        showStatus(output);
    } else if (command == "center") {
        centerAllServos(output);
    } else if (command.startsWith("walk")) {
        int steps = 5; // default
        if (command.indexOf(' ') > 0) {
            steps = command.substring(command.indexOf(' ') + 1).toInt();
        }
        startWalking(steps, output);
    } else if (command == "stop") {
        stopWalking(output);
    } else if (command == "monitor") {
        showRealTimeMonitor(output);
    } else if (command == "imu") {
        showIMUData(output);
    } else if (command == "json") {
        enableJsonMode(output);
    } else {
        output.println("❌ Unknown command: " + command);
        output.println("Type 'help' for available commands");
    }
}

void showStatus(Stream& output) {
    output.println("\n📊 PhoneWalker Status Report");
    output.println("============================");

    output.printf("System: ESP32-S3 @ %d MHz, Free heap: %d bytes\n",
                 getCpuFrequencyMhz(), ESP.getFreeHeap());
    output.printf("Uptime: %lu ms\n", millis());

    output.printf("IMU Status: %s\n", imuData.isConnected ? "✅ Connected" : "❌ Disconnected");
    if (imuData.isConnected) {
        output.printf("  Temperature: %.1f°C\n", imuData.temperature);
        output.printf("  Pitch: %.1f°, Roll: %.1f°\n", imuData.pitch, imuData.roll);
    }

    output.printf("Servos: %d detected\n", servoCount);
    for (int i = 0; i < servoCount; i++) {
        output.printf("  [%d] %s - Position: %d, Status: %s\n",
                     detectedServos[i].id, detectedServos[i].name.c_str(),
                     detectedServos[i].currentPosition,
                     detectedServos[i].isResponding ? "OK" : "ERROR");
    }

    output.printf("Walking: %s\n", walkingActive ? "🚶 Active" : "⏸️ Stopped");
    output.printf("Mode: %s\n", calibrationMode ? "🔧 Calibration" : "🏃 Normal");
}

void centerAllServos(Stream& output) {
    output.println("🎯 Centering all servos to position 2048...");

    for (int i = 0; i < servoCount; i++) {
        output.printf("Enabling torque for servo %d... ", detectedServos[i].id);
        if (servoController.setTorqueEnable(detectedServos[i].id, true)) {
            output.println("✅");
        } else {
            output.println("❌");
        }
        delay(200);

        output.printf("Centering servo %d... ", detectedServos[i].id);
        if (servoController.setPosition(detectedServos[i].id, 2048, 1000)) {
            output.println("✅");
            detectedServos[i].currentPosition = 2048;
        } else {
            output.println("❌");
        }
        delay(200);
    }
    output.println("✅ All servos centered!");
}

void startWalking(int steps, Stream& output) {
    if (servoCount < 4) {
        output.println("❌ Need at least 4 servos for walking simulation");
        return;
    }

    output.printf("🚶 Starting walking simulation with %d steps...\n", steps);
    walkingActive = true;
    setLEDStatus(LED_WALKING);
}

void performWalkStep() {
    // Simple walking simulation
    static int walkPhase = 0;
    int positions[4];

    switch (walkPhase % 4) {
        case 0: // Lift left legs
            positions[0] = 2500; positions[1] = 2048; positions[2] = 1500; positions[3] = 2048;
            break;
        case 1: // Move left legs forward
            positions[0] = 2200; positions[1] = 2048; positions[2] = 1800; positions[3] = 2048;
            break;
        case 2: // Lift right legs
            positions[0] = 2048; positions[1] = 2500; positions[2] = 2048; positions[3] = 1500;
            break;
        case 3: // Move right legs forward
            positions[0] = 2048; positions[1] = 2200; positions[2] = 2048; positions[3] = 1800;
            break;
    }

    for (int i = 0; i < min(4, servoCount); i++) {
        servoController.setPosition(detectedServos[i].id, positions[i], 800);
        detectedServos[i].currentPosition = positions[i];
    }

    walkPhase++;
    USB_SERIAL.printf("🦶 Walk step %d, phase %d\n", walkPhase, walkPhase % 4);
}

void stopWalking(Stream& output) {
    walkingActive = false;
    output.println("⏸️ Walking simulation stopped");
    setLEDStatus(LED_READY);
}

void updateServoPositions() {
    for (int i = 0; i < servoCount; i++) {
        int16_t pos = servoController.getPosition(detectedServos[i].id);
        if (pos >= 0) {
            detectedServos[i].currentPosition = pos;
            detectedServos[i].isResponding = true;
            detectedServos[i].lastUpdate = millis();
        } else {
            detectedServos[i].isResponding = false;
        }
    }
}

void showIMUData(Stream& output) {
    if (!imuData.isConnected) {
        output.println("❌ IMU not connected");
        return;
    }

    output.println("\n📡 IMU Data (GY-521/MPU6050)");
    output.println("============================");
    output.printf("Acceleration (g): X=%.2f, Y=%.2f, Z=%.2f\n",
                 imuData.accelX, imuData.accelY, imuData.accelZ);
    output.printf("Gyroscope (°/s): X=%.1f, Y=%.1f, Z=%.1f\n",
                 imuData.gyroX, imuData.gyroY, imuData.gyroZ);
    output.printf("Orientation: Pitch=%.1f°, Roll=%.1f°\n",
                 imuData.pitch, imuData.roll);
    output.printf("Temperature: %.1f°C\n", imuData.temperature);
}

void showRealTimeMonitor(Stream& output) {
    output.println("📊 Real-time monitoring started (10 seconds)...");

    for (int i = 0; i < 100; i++) {
        updateServoPositions();
        readIMU();

        output.printf("[%d] ", i);
        for (int j = 0; j < min(4, servoCount); j++) {
            output.printf("S%d:%d ", detectedServos[j].id, detectedServos[j].currentPosition);
        }
        if (imuData.isConnected) {
            output.printf("IMU: P%.1f R%.1f", imuData.pitch, imuData.roll);
        }
        output.println();

        delay(100);
    }

    output.println("📊 Monitoring complete");
}

void enableJsonMode(Stream& output) {
    output.println("📱 JSON API mode activated");

    while (true) {
        updateServoPositions();
        readIMU();

        JsonDocument doc;
        doc["timestamp"] = millis();
        doc["system"]["free_heap"] = ESP.getFreeHeap();
        doc["system"]["uptime"] = millis();

        JsonArray servos = doc["servos"].to<JsonArray>();
        for (int i = 0; i < servoCount; i++) {
            JsonObject servo = servos.add<JsonObject>();
            servo["id"] = detectedServos[i].id;
            servo["position"] = detectedServos[i].currentPosition;
            servo["responding"] = detectedServos[i].isResponding;
        }

        if (imuData.isConnected) {
            doc["imu"]["connected"] = true;
            doc["imu"]["accel"]["x"] = imuData.accelX;
            doc["imu"]["accel"]["y"] = imuData.accelY;
            doc["imu"]["accel"]["z"] = imuData.accelZ;
            doc["imu"]["gyro"]["x"] = imuData.gyroX;
            doc["imu"]["gyro"]["y"] = imuData.gyroY;
            doc["imu"]["gyro"]["z"] = imuData.gyroZ;
            doc["imu"]["orientation"]["pitch"] = imuData.pitch;
            doc["imu"]["orientation"]["roll"] = imuData.roll;
            doc["imu"]["temperature"] = imuData.temperature;
        } else {
            doc["imu"]["connected"] = false;
        }

        doc["walking"]["active"] = walkingActive;
        doc["walking"]["mode"] = calibrationMode ? "calibration" : "normal";

        serializeJson(doc, output);
        output.println();

        delay(100);
    }
}