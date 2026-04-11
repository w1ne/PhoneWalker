#!/usr/bin/env python3
"""
Hardware Check - Verify basic setup before protocol debugging
"""

import serial
import time

def check_hardware():
    print("🔧 HARDWARE CHECK")
    print("=================")

    print("Please verify:")
    print("1. ✅ Waveshare adapter has POWER LED on?")
    print("2. ✅ Servo connected to adapter?")
    print("3. ✅ ESP32 connected to adapter RX/TX pins?")
    print("4. ✅ What servo model do you actually have?")

    input("Press Enter when ready...")

def raw_uart_test():
    print("\n🔍 RAW UART TEST")
    print("================")

    try:
        # Try simplest possible communication
        ser = serial.Serial('/dev/ttyACM0', 1000000, timeout=1)
        time.sleep(1)

        print("Sending simple bytes to see ANY response...")

        # Try different simple patterns
        test_patterns = [
            [0xFF, 0xFF],  # Just header
            [0x01, 0x02, 0x03, 0x04],  # Simple pattern
            [0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB],  # Supposed servo ping
        ]

        for i, pattern in enumerate(test_patterns):
            print(f"\nTest {i+1}: Sending {[hex(b) for b in pattern]}")

            # Clear buffer
            while ser.in_waiting > 0:
                ser.read()

            # Send pattern
            ser.write(bytes(pattern))
            time.sleep(0.2)

            # Read ANY response
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"         Got: {[hex(b) for b in response]}")
            else:
                print("         NO RESPONSE")

        ser.close()

    except Exception as e:
        print(f"Error: {e}")

def check_servo_power():
    print("\n⚡ SERVO POWER CHECK")
    print("===================")

    print("Manual checks needed:")
    print("1. Does servo feel warm/energized when you touch it?")
    print("2. Can you manually move the servo horn by hand?")
    print("   - Should be STIFF if powered/torque enabled")
    print("   - Should be LOOSE if no power/torque disabled")
    print("3. Check servo LED (if it has one)")
    print("4. Verify power supply voltage to servos")

if __name__ == "__main__":
    check_hardware()
    raw_uart_test()
    check_servo_power()

    print("\n❓ DIAGNOSIS QUESTIONS:")
    print("======================")
    print("1. Is servo physically stiff or loose?")
    print("2. What exact servo model/part number?")
    print("3. Does Waveshare adapter power LED work?")
    print("4. Any servo movement AT ALL, even slight?")