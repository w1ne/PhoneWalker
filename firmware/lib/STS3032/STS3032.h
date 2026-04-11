#ifndef STS3032_H
#define STS3032_H

#include <Arduino.h>

// STS3032 Register Addresses
#define STS_MODEL_L         3
#define STS_MODEL_H         4
#define STS_VERSION         5
#define STS_ID              6
#define STS_BAUDRATE        7
#define STS_RETURN_DELAY    8
#define STS_RETURN_LEVEL    9
#define STS_MIN_ANGLE_L     10
#define STS_MIN_ANGLE_H     11
#define STS_MAX_ANGLE_L     12
#define STS_MAX_ANGLE_H     13
#define STS_MAX_TEMP        14
#define STS_MAX_INPUT_VOLT  15
#define STS_MIN_INPUT_VOLT  16
#define STS_MAX_TORQUE_L    17
#define STS_MAX_TORQUE_H    18
#define STS_PHASE           19
#define STS_UNLOADING_COND  20
#define STS_LED_ALARM_COND  21
#define STS_P_COEFF         22
#define STS_I_COEFF         23
#define STS_D_COEFF         24
#define STS_G_COEFF         25
#define STS_TORQUE_ENABLE   26
#define STS_GOAL_POSITION_L 27
#define STS_GOAL_POSITION_H 28
#define STS_GOAL_TIME_L     29
#define STS_GOAL_TIME_H     30
#define STS_GOAL_SPEED_L    31
#define STS_GOAL_SPEED_H    32
#define STS_PRESENT_POSITION_L  38
#define STS_PRESENT_POSITION_H  39
#define STS_PRESENT_SPEED_L     40
#define STS_PRESENT_SPEED_H     41
#define STS_PRESENT_LOAD_L      42
#define STS_PRESENT_LOAD_H      43
#define STS_PRESENT_VOLTAGE     44
#define STS_PRESENT_TEMP        45
#define STS_MOVING              46

// Command values
#define STS_INST_PING       0x01
#define STS_INST_READ       0x02
#define STS_INST_WRITE      0x03
#define STS_INST_REG_WRITE  0x04
#define STS_INST_ACTION     0x05
#define STS_INST_RESET      0x06
#define STS_INST_SYNC_WRITE 0x83

// Broadcast ID
#define STS_BROADCAST_ID    0xFE

class STS3032 {
private:
    Stream* serial;
    int dirPin;  // Direction pin for half-duplex communication
    bool halfDuplex;

    void beginTransmission();
    void endTransmission();
    uint8_t calculateChecksum(uint8_t* packet, int length);
    int sendPacket(uint8_t id, uint8_t instruction, uint8_t* parameters, int paramLength);
    int readResponse(uint8_t* buffer, int maxLength);

public:
    STS3032();
    void begin(Stream& serialPort, int directionPin = -1);

    // Basic servo control
    bool ping(uint8_t id);
    bool setPosition(uint8_t id, int16_t position, uint16_t time = 0, uint16_t speed = 0);
    bool setTorqueEnable(uint8_t id, bool enable);

    // Read servo status
    int16_t getPosition(uint8_t id);
    int16_t getSpeed(uint8_t id);
    int16_t getLoad(uint8_t id);
    uint8_t getVoltage(uint8_t id);
    uint8_t getTemperature(uint8_t id);
    bool isMoving(uint8_t id);

    // Parameter configuration
    bool setID(uint8_t oldId, uint8_t newId);
    bool setBaudrate(uint8_t id, uint8_t baudrate);
    bool setAngleLimits(uint8_t id, int16_t minAngle, int16_t maxAngle);
    bool setPIDCoefficients(uint8_t id, uint8_t p, uint8_t i, uint8_t d);

    // Multi-servo control
    bool syncWrite(uint8_t* ids, int16_t* positions, uint16_t* times, uint16_t* speeds, int servoCount);

    // Raw communication
    bool writeRegister(uint8_t id, uint8_t address, uint8_t* data, int length);
    bool readRegister(uint8_t id, uint8_t address, uint8_t* data, int length);

    // Utility functions
    void reset(uint8_t id);
    void resetAll();
    bool scanServos(uint8_t* foundIds, int maxServos);
};

// Convenience class for managing multiple servos as legs
class PhoneWalkerLegs {
private:
    STS3032* servo;
    uint8_t frontLeft, frontRight, backLeft, backRight;
    int16_t neutralPosition;
    int16_t liftHeight;
    int16_t stepLength;

public:
    PhoneWalkerLegs(STS3032* servoController);
    void init(uint8_t fl, uint8_t fr, uint8_t bl, uint8_t br);
    void setNeutralPosition(int16_t position);
    void setGaitParameters(int16_t lift, int16_t step);

    // Basic movements
    bool standUp();
    bool sitDown();
    bool liftLeg(uint8_t leg);
    bool lowerLeg(uint8_t leg);

    // Walking gaits
    bool walkForward(int steps = 1);
    bool walkBackward(int steps = 1);
    bool turnLeft(int steps = 1);
    bool turnRight(int steps = 1);
    bool stop();

    // Individual leg control
    bool setLegPosition(uint8_t leg, int16_t position, uint16_t time = 500);
    int16_t getLegPosition(uint8_t leg);
    bool isLegMoving(uint8_t leg);
};

#endif