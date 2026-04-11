#!/usr/bin/env python3
"""
Debug servo movement - enable torque first
"""

import serial
import time

def send_command(ser, servo_id, instruction, params):
    """Send SCServo command"""
    length = len(params) + 2
    packet = [0xFF, 0xFF, servo_id, length, instruction] + params
    checksum = (~sum(packet[2:])) & 0xFF
    packet.append(checksum)

    ser.write(bytes(packet))
    print(f"Sent: {[hex(b) for b in packet]}")
    time.sleep(0.1)

def enable_torque(ser, servo_id):
    """Enable servo torque"""
    print(f"💪 Enabling torque for servo {servo_id}")
    params = [40, 0, 1]  # Address 40 = Torque Enable, value = 1
    send_command(ser, servo_id, 0x03, params)

def move_servo(ser, servo_id, position, time_ms=1500):
    """Move servo to position"""
    print(f"🎯 Moving servo {servo_id} to position {position}")

    pos_l = position & 0xFF
    pos_h = (position >> 8) & 0xFF
    time_l = time_ms & 0xFF
    time_h = (time_ms >> 8) & 0xFF

    params = [42, 0, pos_l, pos_h, time_l, time_h, 0, 0]
    send_command(ser, servo_id, 0x03, params)

def main():
    print("🔧 Servo Debug Test - With Torque Enable")
    print("=========================================")

    try:
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        time.sleep(1)

        servo_id = 1

        # Step 1: Enable torque (CRITICAL!)
        enable_torque(ser, servo_id)
        time.sleep(1)

        # Step 2: Test big visible movements
        positions = [
            (2048, "CENTER"),
            (1000, "FAR LEFT"),  # Very obvious position
            (3000, "FAR RIGHT"), # Very obvious position
            (2048, "CENTER")
        ]

        for position, name in positions:
            print(f"\n📍 Moving to {name} ({position})")
            move_servo(ser, servo_id, position, 2000)  # Slow movement
            time.sleep(3)  # Wait long enough to see movement
            print("   ⏰ Movement should be complete now")

        print("\n✅ Test complete! Did you see the servo move?")
        ser.close()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()