#!/usr/bin/env python3
"""
🕺 Servo Dance Party! 🕺
Make the servo dance with various choreographed moves!
"""

import serial
import time
import math

def send_servo_command(ser, servo_id, position, time_ms=800):
    """Send position command to servo"""
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

def dance_move_wave(ser, servo_id):
    """🌊 Wave dance move - smooth oscillation"""
    print("🌊 Wave Dance!")
    for i in range(20):
        angle = math.sin(i * 0.5) * 800 + 2048  # Sine wave around center
        position = int(angle)
        send_servo_command(ser, servo_id, position, 150)
        time.sleep(0.15)

def dance_move_shake(ser, servo_id):
    """🥤 Shake dance move - rapid back and forth"""
    print("🥤 Shake it!")
    center = 2048
    for i in range(10):
        # Rapid left-right movement
        send_servo_command(ser, servo_id, center - 300, 100)
        time.sleep(0.1)
        send_servo_command(ser, servo_id, center + 300, 100)
        time.sleep(0.1)

def dance_move_swing(ser, servo_id):
    """🎪 Swing dance move - wide pendulum"""
    print("🎪 Big Swing!")
    positions = [1200, 2900, 1200, 2900, 2048]  # Wide swings, end at center
    for pos in positions:
        send_servo_command(ser, servo_id, pos, 1000)
        time.sleep(1.2)

def dance_move_pulse(ser, servo_id):
    """💓 Pulse dance move - rhythmic pulses"""
    print("💓 Pulse Beat!")
    for i in range(8):
        # Quick pulse out and back
        send_servo_command(ser, servo_id, 2048 + 400, 200)
        time.sleep(0.25)
        send_servo_command(ser, servo_id, 2048, 200)
        time.sleep(0.25)

def dance_move_spiral(ser, servo_id):
    """🌀 Spiral dance move - increasing then decreasing amplitude"""
    print("🌀 Spiral Dance!")
    for i in range(15):
        amplitude = (i if i < 8 else 15-i) * 100
        angle = math.sin(i * 0.8) * amplitude + 2048
        position = int(angle)
        send_servo_command(ser, servo_id, position, 200)
        time.sleep(0.3)

def dance_move_robot(ser, servo_id):
    """🤖 Robot dance move - sharp mechanical movements"""
    print("🤖 Robot Style!")
    positions = [2048, 1500, 2048, 2500, 2048, 1800, 2300, 2048]
    for pos in positions:
        send_servo_command(ser, servo_id, pos, 300)
        time.sleep(0.4)

def dance_party(ser, servo_id):
    """🎉 Full dance party with multiple moves!"""
    print("\n🎉 SERVO DANCE PARTY STARTING! 🎉")
    print("=" * 40)

    # Dance routine
    dance_moves = [
        dance_move_wave,
        dance_move_shake,
        dance_move_swing,
        dance_move_pulse,
        dance_move_spiral,
        dance_move_robot
    ]

    for move in dance_moves:
        move(ser, servo_id)
        time.sleep(0.5)  # Short break between moves

    # Grand finale - return to center with flourish
    print("🎭 Grand Finale!")
    send_servo_command(ser, servo_id, 1500, 500)
    time.sleep(0.6)
    send_servo_command(ser, servo_id, 2500, 500)
    time.sleep(0.6)
    send_servo_command(ser, servo_id, 2048, 800)  # Center
    time.sleep(1)

    print("🎊 Dance party complete! Servo is centered and ready! 🎊")

def main():
    """Main dance function"""
    try:
        print("🎵 Connecting to servo dancer...")
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        time.sleep(1)

        # Enable torque first (same as working servo test)
        print("💪 Enabling servo torque...")
        torque_packet = [0xFF, 0xFF, 1, 5, 0x03, 40, 0, 1, 0xCD]
        ser.write(bytes(torque_packet))
        time.sleep(0.5)

        # Start the dance party!
        dance_party(ser, 1)

        ser.close()

    except Exception as e:
        print(f"❌ Dance error: {e}")
        print("Make sure ESP32 passthrough firmware is running!")

if __name__ == "__main__":
    main()