#!/usr/bin/env python3
"""
Sudo-based servo test - run with: sudo python3 sudo_servo_test.py
"""

import os
import time
import sys

def configure_serial_port():
    """Configure serial port using system commands"""
    print("🔧 Configuring serial port...")

    # Set up serial port: 1000000 baud, 8 data bits, no parity, 1 stop bit
    result = os.system("stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo")

    if result == 0:
        print("✅ Serial port configured for STS3032 communication")
        return True
    else:
        print("❌ Failed to configure serial port")
        return False

def ping_servo(servo_id):
    """Send ping command to servo"""
    print(f"📡 Pinging servo ID {servo_id}...")

    # Calculate checksum for ping packet
    # Format: [0xFF, 0xFF, ID, LENGTH=2, INSTRUCTION=1, CHECKSUM]
    checksum = (~(servo_id + 2 + 1)) & 0xFF
    ping_packet = [0xFF, 0xFF, servo_id, 0x02, 0x01, checksum]

    # Convert to bytes and write to device
    packet_bytes = bytes(ping_packet)

    try:
        with open('/dev/ttyACM0', 'wb', buffering=0) as f:
            f.write(packet_bytes)
        print(f"✅ Ping sent: {[hex(b) for b in packet_bytes]}")
        return True
    except Exception as e:
        print(f"❌ Failed to send ping: {e}")
        return False

def read_response():
    """Read response from servo"""
    print("👂 Listening for response...")

    try:
        with open('/dev/ttyACM0', 'rb', buffering=0) as f:
            # Give servo time to respond
            time.sleep(0.1)

            # Try to read response
            response = f.read(20)  # Read up to 20 bytes

            if response:
                print(f"📥 Response: {[hex(b) for b in response]}")

                if len(response) >= 6:
                    if response[0] == 0xFF and response[1] == 0xFF:
                        servo_id = response[2]
                        length = response[3]
                        error = response[4] if len(response) > 4 else 0

                        print(f"   📍 Servo ID: {servo_id}")
                        print(f"   📏 Length: {length}")

                        if error == 0:
                            print("   ✅ No errors!")
                        else:
                            print(f"   ⚠️  Error code: 0x{error:02X}")
                            decode_error(error)
                        return True
                    else:
                        print("   ❌ Invalid packet header")
                else:
                    print("   ❌ Response too short")
            else:
                print("   ❌ No response received")
                print("   🔍 Check:")
                print("     - Servo power (6-8.4V)")
                print("     - Data line connections")
                print("     - Half-duplex wiring")

    except Exception as e:
        print(f"❌ Failed to read response: {e}")

    return False

def decode_error(error_code):
    """Decode STS3032 error codes"""
    errors = []
    if error_code & 0x01:
        errors.append("Input voltage error (check power supply)")
    if error_code & 0x02:
        errors.append("Angle limit error")
    if error_code & 0x04:
        errors.append("Overheating error")
    if error_code & 0x08:
        errors.append("Range error")
    if error_code & 0x10:
        errors.append("Checksum error (communication problem)")
    if error_code & 0x20:
        errors.append("Overload error (mechanical stress)")
    if error_code & 0x40:
        errors.append("Instruction error")

    for error in errors:
        print(f"     - {error}")

def scan_servos():
    """Scan for servos ID 1-15"""
    print("🔍 Scanning for servos...")
    found_servos = []

    for servo_id in range(1, 16):
        print(f"   Testing ID {servo_id}...", end=" ")

        if ping_servo(servo_id):
            time.sleep(0.05)

            # Quick check for response
            try:
                with open('/dev/ttyACM0', 'rb', buffering=0) as f:
                    response = f.read(10)
                    if response and len(response) >= 4:
                        if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                            found_servos.append(servo_id)
                            print("FOUND!")
                        else:
                            print("No response")
                    else:
                        print("No response")
            except:
                print("Error")
        else:
            print("Send failed")

        time.sleep(0.1)  # Small delay between tests

    if found_servos:
        print(f"\n🎯 Found servos: {found_servos}")
    else:
        print("\n❌ No servos found")
        print("🔧 Troubleshooting:")
        print("   1. Check power supply (6-8.4V, high current)")
        print("   2. Verify data line connections")
        print("   3. Ensure proper grounding")
        print("   4. Check servo IDs (may not be 1-15)")

def main():
    print("🤖 PhoneWalker STS3032 Servo Test (Sudo Mode)")
    print("=" * 45)

    # Check if running as root
    if os.geteuid() != 0:
        print("❌ This script needs to run as root")
        print("💡 Run with: sudo python3 sudo_servo_test.py")
        sys.exit(1)

    # Check if device exists
    if not os.path.exists('/dev/ttyACM0'):
        print("❌ Device /dev/ttyACM0 not found")
        print("🔌 Check USB connection")
        sys.exit(1)

    print("✅ Running as root - can access serial device")
    print("✅ Device /dev/ttyACM0 found")

    if configure_serial_port():

        if len(sys.argv) > 1 and sys.argv[1] == "scan":
            scan_servos()
        else:
            # Test single servo
            ping_servo(1)
            read_response()

            print("\n💡 To scan all servos: sudo python3 sudo_servo_test.py scan")
    else:
        print("❌ Cannot configure serial port")

    print("\n🔋 Remember: STS3032 servos need substantial power!")
    print("   - 6.0V to 8.4V supply voltage")
    print("   - 2-3A per servo peak current")
    print("   - For 15 servos: 30-45A power supply needed!")

if __name__ == "__main__":
    main()