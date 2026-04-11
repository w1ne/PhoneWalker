// PhoneWalker Configuration
#ifndef CONFIG_H
#define CONFIG_H

// Hardware Configuration
#define LED_PIN 21
#define SERVO_UART_RX 18
#define SERVO_UART_TX 17
#define SERVO_UART_BAUD 1000000
#define USB_UART_BAUD 115200

// Servo Configuration
#define MAX_SERVOS 16
#define SERVO_SCAN_START 1
#define SERVO_SCAN_END 16
#define SERVO_RESPONSE_TIMEOUT 100
#define SERVO_MOVE_TIMEOUT 5000

// Default servo positions
#define SERVO_CENTER_POSITION 2048
#define SERVO_MIN_POSITION 0
#define SERVO_MAX_POSITION 4095
#define SERVO_DEFAULT_SPEED 1000
#define SERVO_DEFAULT_TIME 1000

// Dance Configuration
#define MAX_DANCE_STEPS 32
#define DANCE_DEFAULT_TEMPO 1000  // ms between moves
#define DANCE_LOOP_ENABLED true

// Communication settings
#define COMMAND_BUFFER_SIZE 64
#define RESPONSE_BUFFER_SIZE 32

// LED Colors (RGB)
struct Color {
  uint8_t r, g, b;
};

// Status LED colors
const Color LED_STARTUP = {255, 0, 0};    // Red
const Color LED_READY = {0, 255, 0};      // Green
const Color LED_TRANSPARENT = {255, 255, 0}; // Yellow
const Color LED_DANCING = {0, 0, 255};    // Blue
const Color LED_TESTING = {255, 0, 255};  // Purple
const Color LED_ERROR = {255, 0, 0};      // Red

// Debug settings
#define DEBUG_PROTOCOL true
#define DEBUG_SERVO_SCAN true
#define DEBUG_DANCE_MOVES true
#define DEBUG_POSITION_READS true

#endif