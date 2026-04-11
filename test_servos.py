#!/usr/bin/env python3
"""
Quick STS3032 servo communication test
Run this after getting dialout group access
"""

import serial
import time
import sys

def test_servo_communication():
    try:
        # Configure serial port for STS3032
        ser = serial.Serial('/dev/ttyACM0', 1000000, timeout=1)
        print("✓ Serial port opened successfully!")
        print(f"  Port: {ser.name}")
        print(f"  Baudrate: {ser.baudrate}")

        # Test basic communication
        print("\n🔍 Testing servo communication...")

        # Send ping command to servo ID 1
        # STS3032 ping packet: [0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB]
        ping_packet = bytes([0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB])

        print("📤 Sending ping to servo ID 1...")
        ser.write(ping_packet)

        # Wait for response
        time.sleep(0.1)

        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            print(f"📥 Received response: {[hex(b) for b in response]}")

            if len(response) >= 6 and response[0] == 0xFF and response[1] == 0xFF:
                print("✅ Valid servo response detected!")
                servo_id = response[2]
                print(f"   Servo ID: {servo_id}")

                if len(response) >= 5:
                    error = response[4]
                    if error == 0:
                        print("✅ No servo errors!")
                    else:
                        print(f"⚠️  Servo error code: 0x{error:02X}")

                        # Decode common error codes
                        if error & 0x01:
                            print("   - Input voltage error")
                        if error & 0x02:
                            print("   - Angle limit error")
                        if error & 0x04:
                            print("   - Overheating error")
                        if error & 0x08:
                            print("   - Range error")
                        if error & 0x10:
                            print("   - Checksum error")
                        if error & 0x20:
                            print("   - Overload error")
                        if error & 0x40:
                            print("   - Instruction error")
            else:
                print("❌ Invalid response format")
        else:
            print("❌ No response from servo")
            print("   Check:")
            print("   - Servo power (6-8.4V)")
            print("   - Data line connection")
            print("   - Servo ID (default should be 1)")
            print("   - Half-duplex wiring")

        ser.close()

    except serial.SerialException as e:
        print(f"❌ Serial error: {e}")
        print("Make sure you're in the dialout group:")
        print("  sudo usermod -a -G dialout $USER")
        print("  Then logout and login again")

    except ImportError:
        print("❌ PySerial not installed")
        print("Install with: pip3 install pyserial")

def scan_servos():
    """Scan for servo IDs 1-15"""
    try:
        ser = serial.Serial('/dev/ttyACM0', 1000000, timeout=0.5)
        print("🔍 Scanning for servos (IDs 1-15)...")

        found_servos = []

        for servo_id in range(1, 16):
            # Create ping packet for this servo ID
            # Format: [0xFF, 0xFF, ID, LENGTH, INSTRUCTION, CHECKSUM]
            checksum = (~(servo_id + 2 + 1)) & 0xFF
            ping_packet = bytes([0xFF, 0xFF, servo_id, 0x02, 0x01, checksum])

            ser.write(ping_packet)
            time.sleep(0.05)

            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                if len(response) >= 6 and response[0] == 0xFF and response[1] == 0xFF:
                    if response[2] == servo_id:
                        found_servos.append(servo_id)
                        print(f"  ✅ Found servo ID {servo_id}")

                        # Check for errors
                        if len(response) >= 5 and response[4] != 0:
                            error = response[4]
                            print(f"     ⚠️  Error code: 0x{error:02X}")
            else:
                print(f"  ❌ No response from ID {servo_id}")

        ser.close()

        if found_servos:
            print(f"\n🎯 Found {len(found_servos)} servos: {found_servos}")
        else:
            print("\n❌ No servos found!")
            print("Check power supply and connections")

    except Exception as e:
        print(f"Error during scan: {e}")

if __name__ == "__main__":
    print("PhoneWalker STS3032 Servo Test")
    print("=" * 30)

    if len(sys.argv) > 1 and sys.argv[1] == "scan":
        scan_servos()
    else:
        test_servo_communication()
        print("\nTo scan all servos: python3 test_servos.py scan")