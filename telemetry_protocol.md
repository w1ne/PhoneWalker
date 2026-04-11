# PhoneWalker Telemetry Protocol Design

## Overview
Periodic status reporting from robot to phone/controller with real-time servo positions and system health.

## Protocol Structure

### 1. Status Packet Format
```json
{
  "timestamp": 1648123456789,
  "robot_id": "PW001", 
  "status": "active|idle|error|dancing",
  "uptime_ms": 45678,
  "free_heap": 365000,
  "servos": [
    {
      "id": 1,
      "position": 2048,
      "target": 2048, 
      "moving": false,
      "load": 15,
      "voltage": 7.2,
      "temperature": 32,
      "online": true,
      "error_count": 0
    }
  ],
  "imu": {
    "pitch": 1.5,
    "roll": -2.3,
    "yaw": 0.0,
    "accel_x": 0.1,
    "accel_y": 9.8,
    "accel_z": 0.0
  },
  "commands_processed": 156,
  "last_command": "dance_wave",
  "battery_voltage": 8.1
}
```

### 2. Reporting Frequencies
- **Fast telemetry** (10Hz): Servo positions, IMU, movement status
- **Slow telemetry** (1Hz): System health, temperatures, battery
- **Event-driven**: Errors, command completion, servo failures

### 3. Communication Methods

#### Option A: WiFi/TCP
```cpp
void sendTelemetry() {
  StaticJsonDocument<1024> doc;
  doc["timestamp"] = millis();
  doc["robot_id"] = "PW001";
  doc["status"] = getCurrentStatus();
  
  JsonArray servos = doc.createNestedArray("servos");
  for(int i = 0; i < servoCount; i++) {
    JsonObject servo = servos.createNestedObject();
    servo["id"] = detectedServos[i].id;
    servo["position"] = readServoPosition(detectedServos[i].id);
    servo["online"] = pingServo(detectedServos[i].id);
  }
  
  sendToPhone(doc);
}
```

#### Option B: USB Serial Stream
```cpp
void streamTelemetry() {
  Serial.printf("TEL|%lu|%s|", millis(), getCurrentStatus());
  for(int i = 0; i < servoCount; i++) {
    Serial.printf("S%d:%d,", detectedServos[i].id, readServoPosition(detectedServos[i].id));
  }
  Serial.printf("IMU:%.1f,%.1f,%.1f|", imu.pitch, imu.roll, imu.yaw);
  Serial.println();
}
```

### 4. Command Response Protocol

#### Phone → Robot Commands
```json
{
  "command": "dance_wave",
  "params": {"speed": 1.0, "duration": 10000},
  "id": "cmd_123"
}
```

#### Robot → Phone Acknowledgment  
```json
{
  "ack": "cmd_123",
  "status": "started|completed|error",
  "message": "Wave dance started",
  "estimated_duration": 10000
}
```

### 5. Emergency/Error Reporting
```json
{
  "alert": "servo_error",
  "severity": "critical|warning|info", 
  "servo_id": 2,
  "details": "Position feedback timeout",
  "timestamp": 1648123456789,
  "recovery_action": "retry|disable|restart"
}
```

### 6. Performance Metrics
- Servo response times
- Command execution times
- Communication round-trip latency
- Position accuracy (target vs actual)
- Movement smoothness metrics

## Implementation Strategy

### Phase 1: Basic Status
- Servo positions every 100ms
- System status every 1s
- USB serial output format

### Phase 2: Phone Integration  
- WiFi connection to phone
- JSON telemetry packets
- Command/response protocol

### Phase 3: Advanced Monitoring
- Performance metrics
- Predictive error detection
- Autonomous recovery

### Phone App Features
- Real-time position visualization
- Performance graphs
- Error logs and alerts
- Remote control interface
- Dance choreography editor

## Benefits
- **Real-time monitoring** of all servo positions
- **Predictive maintenance** through error pattern detection
- **Remote debugging** capability
- **Performance optimization** data
- **Autonomous operation** with full visibility