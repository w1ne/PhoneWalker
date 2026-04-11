#!/usr/bin/env python3
"""
Test single servo movement through ESP32 with PhoneWalker firmware
We'll switch to passthrough mode and test direct servo control
"""

import serial
import time

def send_servo_command(ser, servo_id, position, time_ms=1000):
    """Send position command to servo using SCServo protocol"""
    print(f"Moving servo {servo_id} to position {position}")

    # STS series position command: instruction 0x03
    pos_l = position & 0xFF
    pos_h = (position >> 8) & 0xFF
    time_l = time_ms & 0xFF
    time_h = (time_ms >> 8) & 0xFF

    # Address 42 (0x2A) = Goal Position for STS series
    params = [42, 0, pos_l, pos_h, time_l, time_h, 0, 0]

    # Build packet
    packet = [0xFF, 0xFF, servo_id, len(params) + 2, 0x03] + params
    checksum = (~sum(packet[2:])) & 0xFF
    packet.append(checksum)

    ser.write(bytes(packet))
    print(f"Sent: {[hex(b) for b in packet]}")

def test_servo_movement():
    """Test servo movement with different positions"""
    print("Testing servo movement through PhoneWalker firmware")

    try:
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        time.sleep(1)

        # Test different positions
        positions = [2048, 1500, 2500, 2048]  # center, left, right, center

        for pos in positions:
            send_servo_command(ser, 1, pos, 1500)
            time.sleep(2)

        ser.close()
        print("✅ Movement test completed")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_servo_movement()