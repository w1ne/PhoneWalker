#!/usr/bin/env python3
"""
SIMPLE test - just see if ANYTHING happens
"""

import serial
import time

def basic_test():
    print("🔍 BASIC SERVO TEST")
    print("===================")
    print("Goal: See if servo responds AT ALL")

    ser = serial.Serial('/dev/ttyACM0', 1000000, timeout=1)
    time.sleep(1)

    # Try the simplest possible servo command - just enable torque
    print("\n1. Trying to enable torque...")
    torque_cmd = bytes([0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD])

    ser.write(torque_cmd)
    time.sleep(1)

    print("   Command sent - servo should become STIFF if working")
    print("   Try to manually move the servo horn by hand")
    print("   If it's stiff = torque enabled = communication working")
    print("   If it's loose = no communication or no power")

    # Try a big obvious movement
    print("\n2. Trying BIG movement to position 1000...")
    move_cmd = bytes([0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0xE8, 0x03, 0xE8, 0x03, 0x00, 0x00, 0x2B])

    ser.write(move_cmd)
    time.sleep(3)

    print("   Big movement command sent")
    print("   Servo should move to extreme position")

    # Try opposite direction
    print("\n3. Trying opposite direction to position 3000...")
    move_cmd2 = bytes([0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0xB8, 0x0B, 0xE8, 0x03, 0x00, 0x00, 0x55])

    ser.write(move_cmd2)
    time.sleep(3)

    print("   Opposite movement command sent")

    ser.close()

    print("\n❓ DID YOU SEE:")
    print("- Servo become stiff after torque enable?")
    print("- ANY movement at all?")
    print("- Any sounds from servo?")
    print("- Any LED changes?")

if __name__ == "__main__":
    basic_test()