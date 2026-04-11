#!/usr/bin/env python3
"""
🎭 Coordinated Servo Dance using existing working functions
Uses the proven scservo_working_example.py functions for position feedback
"""

import serial
import time
from scservo_working_example import *

def coordinated_dance_routine(ser, servo_ids):
    """🎭 Full coordinated dance using position feedback"""
    print("\n🎉 COORDINATED SERVO DANCE STARTING! 🎉")
    print("Using existing position feedback functions")
    print("=" * 50)

    # Dance sequence with position monitoring
    dance_moves = [
        {
            'name': '🎯 Center All Servos',
            'positions': {sid: 2048 for sid in servo_ids},
            'time': 1000
        },
        {
            'name': '🌊 Wave Formation',
            'positions': {servo_ids[0]: 1500} if len(servo_ids) >= 1 else {},
            'time': 800
        },
        {
            'name': '🤝 Synchronized Swing',
            'positions': {sid: 2500 for sid in servo_ids},
            'time': 600
        },
        {
            'name': '💫 Alternating Pattern',
            'positions': {sid: (1800 if i % 2 == 0 else 2300)
                         for i, sid in enumerate(servo_ids)},
            'time': 500
        },
        {
            'name': '🎪 Big Finale',
            'positions': {servo_ids[0]: 1200} if len(servo_ids) >= 1 else {},
            'time': 800
        },
        {
            'name': '🏠 Return Home',
            'positions': {sid: 2048 for sid in servo_ids},
            'time': 1000
        }
    ]

    # Execute dance with position feedback
    for i, move in enumerate(dance_moves):
        print(f"\n--- Step {i+1}: {move['name']} ---")

        # Enable torque for all servos
        for servo_id in move['positions'].keys():
            enable_torque(ser, servo_id, True)
            time.sleep(0.1)

        # Read current positions before moving
        print("📊 Current positions:")
        current_positions = {}
        for servo_id in servo_ids:
            pos = read_position(ser, servo_id)
            current_positions[servo_id] = pos
            if pos is not None:
                print(f"  Servo {servo_id}: {pos}")

        # Send movement commands
        print("🎯 Target positions:")
        for servo_id, target_pos in move['positions'].items():
            print(f"  Servo {servo_id}: {current_positions.get(servo_id, 'unknown')} → {target_pos}")
            set_position(ser, servo_id, target_pos, move['time'])
            time.sleep(0.1)

        # Wait for movement completion
        time.sleep(move['time'] / 1000.0 + 0.5)

        # Read final positions for feedback
        print("✅ Final positions:")
        for servo_id in servo_ids:
            final_pos = read_position(ser, servo_id)
            target_pos = move['positions'].get(servo_id, current_positions.get(servo_id))
            if final_pos is not None and target_pos is not None:
                error = abs(final_pos - target_pos)
                status = "✅" if error < 50 else "⚠️"
                print(f"  Servo {servo_id}: {final_pos} {status} (target: {target_pos}, error: {error})")

        time.sleep(0.5)

    print("\n🎊 Coordinated dance complete! All servos positioned with feedback! 🎊")

def main():
    """Main coordinated dance function"""
    print("🎭 Coordinated Servo Dance with Position Feedback")
    print("Using proven working SCServo functions")
    print("=" * 50)

    try:
        # Use existing working test function to find servos
        ser = serial.Serial('/dev/ttyACM0', 1000000, timeout=1)
        time.sleep(0.1)

        # Find servos using existing ping function
        print("🔍 Discovering servos using existing functions...")
        found_servos = []
        for servo_id in range(1, 16):
            if ping_servo(ser, servo_id):
                found_servos.append(servo_id)
            time.sleep(0.1)

        if not found_servos:
            print("❌ No servos found! Make sure hardware is connected.")
            return

        print(f"🎯 Found servos: {found_servos}")

        # Run coordinated dance
        coordinated_dance_routine(ser, found_servos[:4])  # Max 4 servos

        ser.close()
        print("🎉 Dance session complete!")

    except Exception as e:
        print(f"❌ Dance error: {e}")

if __name__ == "__main__":
    main()