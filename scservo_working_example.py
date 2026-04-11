#!/usr/bin/env python3
"""
Working SCServo STS3032 example
Based on actual working examples from SCServo library
"""

import serial
import time

def calculate_checksum(params):
    """Calculate SCServo checksum"""
    return (~sum(params)) & 0xFF

def send_command(ser, servo_id, instruction, params):
    """Send SCServo command packet"""
    length = len(params) + 2  # params + instruction + checksum

    # Build packet: [0xFF, 0xFF, ID, LENGTH, INSTRUCTION, PARAMS..., CHECKSUM]
    packet = [0xFF, 0xFF, servo_id, length, instruction] + params
    checksum = calculate_checksum(packet[2:])  # Calculate from ID onwards
    packet.append(checksum)

    # Send packet
    ser.write(bytes(packet))
    print(f"Sent: {[hex(b) for b in packet]}")

def ping_servo(ser, servo_id):
    """Ping servo to check if it responds"""
    print(f"Pinging servo {servo_id}...")
    send_command(ser, servo_id, 0x01, [])  # Ping instruction

    # Read response
    time.sleep(0.1)
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"Response: {[hex(b) for b in response]}")
        return len(response) > 0
    else:
        print("No response")
        return False

def set_position(ser, servo_id, position, time_ms=1000):
    """Set servo position using SCServo protocol"""
    print(f"Moving servo {servo_id} to position {position}")

    # STS series position command: instruction 0x03
    # Parameters: [START_ADDR_L, START_ADDR_H, POS_L, POS_H, TIME_L, TIME_H, SPEED_L, SPEED_H]
    pos_l = position & 0xFF
    pos_h = (position >> 8) & 0xFF
    time_l = time_ms & 0xFF
    time_h = (time_ms >> 8) & 0xFF

    # Address 42 (0x2A) = Goal Position for STS series
    params = [42, 0, pos_l, pos_h, time_l, time_h, 0, 0]
    send_command(ser, servo_id, 0x03, params)

def enable_torque(ser, servo_id, enable=True):
    """Enable/disable servo torque"""
    print(f"{'Enabling' if enable else 'Disabling'} torque for servo {servo_id}")

    # Address 40 (0x28) = Torque Enable
    params = [40, 0, 1 if enable else 0]
    send_command(ser, servo_id, 0x03, params)

def read_position(ser, servo_id):
    """Read current servo position"""
    print(f"Reading position from servo {servo_id}...")

    # Read instruction: 0x02
    # Parameters: [START_ADDR_L, START_ADDR_H, LENGTH_L, LENGTH_H]
    # Address 56 (0x38) = Present Position (2 bytes)
    params = [56, 0, 2, 0]
    send_command(ser, servo_id, 0x02, params)

    # Read response
    time.sleep(0.1)
    if ser.in_waiting > 0:
        response = ser.read(ser.in_waiting)
        print(f"Position response: {[hex(b) for b in response]}")
        if len(response) >= 7:
            pos = response[5] | (response[6] << 8)
            print(f"Current position: {pos}")
            return pos
    return None

def test_scservo():
    """Test SCServo communication"""
    print("SCServo STS3032 Test")
    print("===================")

    try:
        # Try different baud rates
        for baud in [1000000, 500000, 115200]:
            print(f"\nTesting at {baud} baud...")

            ser = serial.Serial('/dev/ttyACM0', baud, timeout=1)
            time.sleep(0.1)

            # Test ping on multiple servo IDs
            found_servos = []
            for servo_id in range(1, 16):
                if ping_servo(ser, servo_id):
                    found_servos.append(servo_id)
                time.sleep(0.1)

            if found_servos:
                print(f"Found servos at {baud} baud: {found_servos}")

                # Test movement
                for servo_id in found_servos[:4]:  # Test first 4
                    enable_torque(ser, servo_id, True)
                    time.sleep(0.2)

                    # Test positions
                    for pos in [1500, 2500, 2048]:
                        set_position(ser, servo_id, pos, 1000)
                        time.sleep(2)
                        read_position(ser, servo_id)
                        time.sleep(0.5)

                ser.close()
                return True

            ser.close()

    except Exception as e:
        print(f"Error: {e}")

    print("\nNo working servos found!")
    return False

if __name__ == "__main__":
    test_scservo()