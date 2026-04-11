#!/usr/bin/env python3
"""
FIXED Communication Test - Use correct baud rate
"""

import serial
import time

def test_working_communication():
    """Test with CORRECT baud rate from debug results"""
    print("🔧 FIXED COMMUNICATION TEST")
    print("=" * 40)

    # Use the working baud rate from our debug test
    CORRECT_BAUD = 1000000

    try:
        ser = serial.Serial('/dev/ttyACM0', CORRECT_BAUD, timeout=1)
        time.sleep(1)

        print(f"Using CORRECT baud rate: {CORRECT_BAUD}")

        # Test sequence with proper timing
        tests = [
            {
                'name': 'PING Test',
                'packet': [0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB],
                'wait': 0.1
            },
            {
                'name': 'Enable Torque',
                'packet': [0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD],
                'wait': 0.2
            },
            {
                'name': 'Move to Center (2048)',
                'packet': [0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00, 0xD4],
                'wait': 1.5  # Wait for movement
            },
            {
                'name': 'Read Position',
                'packet': [0xFF, 0xFF, 0x01, 0x06, 0x02, 0x38, 0x00, 0x02, 0x00, 0xBC],
                'wait': 0.1
            },
            {
                'name': 'Move to Left (1500)',
                'packet': [0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0xDC, 0x05, 0xE8, 0x03, 0x00, 0x00, 0xFB],
                'wait': 1.5
            },
            {
                'name': 'Read Position Again',
                'packet': [0xFF, 0xFF, 0x01, 0x06, 0x02, 0x38, 0x00, 0x02, 0x00, 0xBC],
                'wait': 0.1
            }
        ]

        success_count = 0

        for test in tests:
            print(f"\n📋 {test['name']}")

            # Clear buffer
            while ser.in_waiting > 0:
                ser.read()

            # Send command
            ser.write(bytes(test['packet']))
            print(f"   SENT: {[hex(b) for b in test['packet']]}")

            # Wait appropriate time
            time.sleep(test['wait'])

            # Read response
            if ser.in_waiting > 0:
                response = list(ser.read(ser.in_waiting))
                print(f"   RECV: {[hex(b) for b in response]}")

                # Check if response is valid
                if len(response) >= 6 and response[0] == 0xFF and response[1] == 0xFF:
                    servo_id = response[2]
                    length = response[3]
                    error = response[4]

                    if error == 0:
                        print(f"   ✅ SUCCESS - Servo {servo_id} responded correctly")
                        success_count += 1
                    else:
                        print(f"   ⚠️ Servo {servo_id} error code: {error}")
                else:
                    print(f"   ❌ Invalid response format")
            else:
                print(f"   ❌ NO RESPONSE")

        print(f"\n📊 RESULTS: {success_count}/{len(tests)} tests successful")

        if success_count >= len(tests) * 0.8:  # 80% success rate
            print("🎉 COMMUNICATION WORKING!")
        elif success_count > 0:
            print("⚠️ PARTIAL SUCCESS - Some issues remain")
        else:
            print("❌ STILL NOT WORKING")

        ser.close()
        return success_count >= len(tests) * 0.8

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    working = test_working_communication()

    if working:
        print("\n✅ COMMUNICATION BUG FIXED!")
        print("Now we can implement this in firmware.")
    else:
        print("\n❌ Still debugging needed.")
        print("Check hardware connections.")