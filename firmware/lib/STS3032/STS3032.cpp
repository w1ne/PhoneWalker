#include "STS3032.h"

STS3032::STS3032() {
    serial = nullptr;
    dirPin = -1;
    halfDuplex = false;
}

void STS3032::begin(Stream& serialPort, int directionPin) {
    serial = &serialPort;
    dirPin = directionPin;
    halfDuplex = (directionPin >= 0);

    if (halfDuplex) {
        pinMode(dirPin, OUTPUT);
        digitalWrite(dirPin, LOW);  // Start in receive mode
    }
}

void STS3032::beginTransmission() {
    if (halfDuplex) {
        digitalWrite(dirPin, HIGH);  // Switch to transmit mode
        delayMicroseconds(10);       // Small delay for line settling
    }
}

void STS3032::endTransmission() {
    if (halfDuplex) {
        serial->flush();             // Wait for transmission to complete
        delayMicroseconds(10);
        digitalWrite(dirPin, LOW);   // Switch back to receive mode
    }
}

uint8_t STS3032::calculateChecksum(uint8_t* packet, int length) {
    uint16_t sum = 0;
    for (int i = 2; i < length - 1; i++) {  // Skip header bytes and checksum
        sum += packet[i];
    }
    return (~sum) & 0xFF;
}

int STS3032::sendPacket(uint8_t id, uint8_t instruction, uint8_t* parameters, int paramLength) {
    if (!serial) return -1;

    int packetLength = 6 + paramLength;  // Header(2) + ID(1) + Length(1) + Instruction(1) + Params + Checksum(1)
    uint8_t packet[packetLength];

    // Build packet
    packet[0] = 0xFF;  // Header
    packet[1] = 0xFF;  // Header
    packet[2] = id;
    packet[3] = paramLength + 2;  // Length = parameters + instruction + checksum
    packet[4] = instruction;

    // Copy parameters
    for (int i = 0; i < paramLength; i++) {
        packet[5 + i] = parameters[i];
    }

    // Calculate and add checksum
    packet[packetLength - 1] = calculateChecksum(packet, packetLength);

    // Send packet
    beginTransmission();
    serial->write(packet, packetLength);
    endTransmission();

    return packetLength;
}

int STS3032::readResponse(uint8_t* buffer, int maxLength) {
    if (!serial) return -1;

    unsigned long timeout = millis() + 100;  // 100ms timeout
    int bytesRead = 0;

    // Wait for response
    while (millis() < timeout && bytesRead < maxLength) {
        if (serial->available()) {
            buffer[bytesRead] = serial->read();
            bytesRead++;

            // Check for valid header
            if (bytesRead >= 2 && (buffer[0] != 0xFF || buffer[1] != 0xFF)) {
                // Invalid header, reset
                bytesRead = 0;
                continue;
            }

            // Check if we have enough bytes to read the length
            if (bytesRead >= 4) {
                int expectedLength = 4 + buffer[3];  // Header(2) + ID(1) + Length(1) + Data
                if (bytesRead >= expectedLength) {
                    // Verify checksum
                    uint8_t receivedChecksum = buffer[expectedLength - 1];
                    uint8_t calculatedChecksum = calculateChecksum(buffer, expectedLength);

                    if (receivedChecksum == calculatedChecksum) {
                        return bytesRead;
                    } else {
                        // Invalid checksum, reset
                        bytesRead = 0;
                    }
                }
            }
        }
    }

    return bytesRead;  // Might be 0 if timeout or incomplete
}

bool STS3032::ping(uint8_t id) {
    uint8_t buffer[16];

    if (sendPacket(id, STS_INST_PING, nullptr, 0) < 0) {
        return false;
    }

    int responseLength = readResponse(buffer, 16);
    return (responseLength >= 6 && buffer[2] == id);
}

bool STS3032::setPosition(uint8_t id, int16_t position, uint16_t time, uint16_t speed) {
    uint8_t params[6];

    params[0] = position & 0xFF;        // Position low byte
    params[1] = (position >> 8) & 0xFF; // Position high byte
    params[2] = time & 0xFF;            // Time low byte
    params[3] = (time >> 8) & 0xFF;     // Time high byte
    params[4] = speed & 0xFF;           // Speed low byte
    params[5] = (speed >> 8) & 0xFF;    // Speed high byte

    return writeRegister(id, STS_GOAL_POSITION_L, params, 6);
}

bool STS3032::setTorqueEnable(uint8_t id, bool enable) {
    uint8_t value = enable ? 1 : 0;
    return writeRegister(id, STS_TORQUE_ENABLE, &value, 1);
}

int16_t STS3032::getPosition(uint8_t id) {
    uint8_t data[2];
    if (readRegister(id, STS_PRESENT_POSITION_L, data, 2)) {
        return (int16_t)(data[0] | (data[1] << 8));
    }
    return -1;
}

int16_t STS3032::getSpeed(uint8_t id) {
    uint8_t data[2];
    if (readRegister(id, STS_PRESENT_SPEED_L, data, 2)) {
        return (int16_t)(data[0] | (data[1] << 8));
    }
    return -1;
}

int16_t STS3032::getLoad(uint8_t id) {
    uint8_t data[2];
    if (readRegister(id, STS_PRESENT_LOAD_L, data, 2)) {
        return (int16_t)(data[0] | (data[1] << 8));
    }
    return -1;
}

uint8_t STS3032::getVoltage(uint8_t id) {
    uint8_t data;
    if (readRegister(id, STS_PRESENT_VOLTAGE, &data, 1)) {
        return data;
    }
    return 0;
}

uint8_t STS3032::getTemperature(uint8_t id) {
    uint8_t data;
    if (readRegister(id, STS_PRESENT_TEMP, &data, 1)) {
        return data;
    }
    return 0;
}

bool STS3032::isMoving(uint8_t id) {
    uint8_t data;
    if (readRegister(id, STS_MOVING, &data, 1)) {
        return data != 0;
    }
    return false;
}

bool STS3032::writeRegister(uint8_t id, uint8_t address, uint8_t* data, int length) {
    uint8_t params[length + 1];
    params[0] = address;

    for (int i = 0; i < length; i++) {
        params[i + 1] = data[i];
    }

    if (sendPacket(id, STS_INST_WRITE, params, length + 1) < 0) {
        return false;
    }

    // Read response if not broadcasting
    if (id != STS_BROADCAST_ID) {
        uint8_t buffer[16];
        int responseLength = readResponse(buffer, 16);
        return (responseLength >= 6 && buffer[2] == id && buffer[4] == 0);
    }

    return true;
}

bool STS3032::readRegister(uint8_t id, uint8_t address, uint8_t* data, int length) {
    uint8_t params[2];
    params[0] = address;
    params[1] = length;

    if (sendPacket(id, STS_INST_READ, params, 2) < 0) {
        return false;
    }

    uint8_t buffer[16];
    int responseLength = readResponse(buffer, 16);

    if (responseLength >= (6 + length) && buffer[2] == id && buffer[4] == 0) {
        for (int i = 0; i < length; i++) {
            data[i] = buffer[5 + i];
        }
        return true;
    }

    return false;
}

bool STS3032::syncWrite(uint8_t* ids, int16_t* positions, uint16_t* times, uint16_t* speeds, int servoCount) {
    int paramLength = 1 + 6 + servoCount * 7;  // Address + data_length + (id + 6 bytes) per servo
    uint8_t params[paramLength];
    int index = 0;

    params[index++] = STS_GOAL_POSITION_L;  // Starting address
    params[index++] = 6;                    // Data length per servo

    for (int i = 0; i < servoCount; i++) {
        params[index++] = ids[i];                           // Servo ID
        params[index++] = positions[i] & 0xFF;              // Position low
        params[index++] = (positions[i] >> 8) & 0xFF;       // Position high
        params[index++] = times[i] & 0xFF;                  // Time low
        params[index++] = (times[i] >> 8) & 0xFF;           // Time high
        params[index++] = speeds[i] & 0xFF;                 // Speed low
        params[index++] = (speeds[i] >> 8) & 0xFF;          // Speed high
    }

    return sendPacket(STS_BROADCAST_ID, STS_INST_SYNC_WRITE, params, paramLength) > 0;
}

bool STS3032::scanServos(uint8_t* foundIds, int maxServos) {
    int foundCount = 0;

    for (uint8_t id = 1; id < 254 && foundCount < maxServos; id++) {
        if (ping(id)) {
            foundIds[foundCount++] = id;
        }
        delay(10);  // Small delay between pings
    }

    return foundCount > 0;
}

void STS3032::reset(uint8_t id) {
    sendPacket(id, STS_INST_RESET, nullptr, 0);
    delay(1000);  // Wait for servo to reset
}

void STS3032::resetAll() {
    reset(STS_BROADCAST_ID);
}

// PhoneWalkerLegs implementation

PhoneWalkerLegs::PhoneWalkerLegs(STS3032* servoController) {
    servo = servoController;
    neutralPosition = 2048;  // Center position (0-4095 range)
    liftHeight = 200;        // How high to lift legs
    stepLength = 150;        // How far to step forward/backward
}

void PhoneWalkerLegs::init(uint8_t fl, uint8_t fr, uint8_t bl, uint8_t br) {
    frontLeft = fl;
    frontRight = fr;
    backLeft = bl;
    backRight = br;
}

void PhoneWalkerLegs::setNeutralPosition(int16_t position) {
    neutralPosition = position;
}

void PhoneWalkerLegs::setGaitParameters(int16_t lift, int16_t step) {
    liftHeight = lift;
    stepLength = step;
}

bool PhoneWalkerLegs::standUp() {
    // Enable torque for all servos
    servo->setTorqueEnable(frontLeft, true);
    servo->setTorqueEnable(frontRight, true);
    servo->setTorqueEnable(backLeft, true);
    servo->setTorqueEnable(backRight, true);

    // Move all legs to neutral position
    servo->setPosition(frontLeft, neutralPosition, 1000);
    servo->setPosition(frontRight, neutralPosition, 1000);
    servo->setPosition(backLeft, neutralPosition, 1000);
    servo->setPosition(backRight, neutralPosition, 1000);

    delay(1500);  // Wait for movement to complete
    return true;
}

bool PhoneWalkerLegs::sitDown() {
    // Lower all legs
    int16_t sitPosition = neutralPosition + liftHeight;

    servo->setPosition(frontLeft, sitPosition, 1000);
    servo->setPosition(frontRight, sitPosition, 1000);
    servo->setPosition(backLeft, sitPosition, 1000);
    servo->setPosition(backRight, sitPosition, 1000);

    delay(1500);  // Wait for movement to complete

    // Disable torque to allow free movement
    servo->setTorqueEnable(frontLeft, false);
    servo->setTorqueEnable(frontRight, false);
    servo->setTorqueEnable(backLeft, false);
    servo->setTorqueEnable(backRight, false);

    return true;
}

bool PhoneWalkerLegs::walkForward(int steps) {
    for (int step = 0; step < steps; step++) {
        // Lift front-left and back-right legs
        servo->setPosition(frontLeft, neutralPosition - liftHeight, 300);
        servo->setPosition(backRight, neutralPosition - liftHeight, 300);
        delay(400);

        // Move lifted legs forward and grounded legs backward
        servo->setPosition(frontLeft, neutralPosition - liftHeight, 200);
        servo->setPosition(backRight, neutralPosition - liftHeight, 200);
        servo->setPosition(frontRight, neutralPosition + stepLength/2, 400);
        servo->setPosition(backLeft, neutralPosition + stepLength/2, 400);
        delay(500);

        // Lower front-left and back-right legs
        servo->setPosition(frontLeft, neutralPosition, 200);
        servo->setPosition(backRight, neutralPosition, 200);
        delay(300);

        // Lift front-right and back-left legs
        servo->setPosition(frontRight, neutralPosition - liftHeight, 300);
        servo->setPosition(backLeft, neutralPosition - liftHeight, 300);
        delay(400);

        // Move lifted legs forward and grounded legs backward
        servo->setPosition(frontRight, neutralPosition - liftHeight, 200);
        servo->setPosition(backLeft, neutralPosition - liftHeight, 200);
        servo->setPosition(frontLeft, neutralPosition + stepLength/2, 400);
        servo->setPosition(backRight, neutralPosition + stepLength/2, 400);
        delay(500);

        // Lower front-right and back-left legs
        servo->setPosition(frontRight, neutralPosition, 200);
        servo->setPosition(backLeft, neutralPosition, 200);
        delay(300);
    }

    return true;
}

bool PhoneWalkerLegs::setLegPosition(uint8_t leg, int16_t position, uint16_t time) {
    return servo->setPosition(leg, position, time);
}

int16_t PhoneWalkerLegs::getLegPosition(uint8_t leg) {
    return servo->getPosition(leg);
}

bool PhoneWalkerLegs::isLegMoving(uint8_t leg) {
    return servo->isMoving(leg);
}

bool PhoneWalkerLegs::stop() {
    // Stop all movement by setting current positions as goals
    servo->setPosition(frontLeft, servo->getPosition(frontLeft), 0);
    servo->setPosition(frontRight, servo->getPosition(frontRight), 0);
    servo->setPosition(backLeft, servo->getPosition(backLeft), 0);
    servo->setPosition(backRight, servo->getPosition(backRight), 0);

    return true;
}