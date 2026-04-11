#!/usr/bin/env python3
"""
Communication Test - Compare Working vs Broken
Capture exact communication patterns to find bugs
"""

import serial
import time

def capture_communication():
    """Test basic servo communication and capture responses"""
    print("🔍 COMMUNICATION DEBUG TEST")
    print("=" * 50)

    try:
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        time.sleep(1)

        tests = [
            {
                'name': 'PING Test',
                'packet': [0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB],
                'expected_response_length': 6,
                'description': 'Basic ping to see if servo responds'
            },
            {
                'name': 'Enable Torque',
                'packet': [0xFF, 0xFF, 0x01, 0x05, 0x03, 0x28, 0x00, 0x01, 0xCD],
                'expected_response_length': 6,
                'description': 'Enable torque for movement'
            },
            {
                'name': 'Read Position',
                'packet': [0xFF, 0xFF, 0x01, 0x06, 0x02, 0x38, 0x00, 0x02, 0x00, 0xBC],
                'expected_response_length': 8,
                'description': 'Read current servo position'
            },
            {
                'name': 'Move to 2048',
                'packet': [0xFF, 0xFF, 0x01, 0x0A, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00, 0xD4],
                'expected_response_length': 6,
                'description': 'Move servo to center position'
            }
        ]

        working_communication = []

        for test in tests:
            print(f"\n📋 {test['name']}")
            print(f"   Description: {test['description']}")
            print(f"   Sending: {[hex(b) for b in test['packet']]}")

            # Clear any existing data
            while ser.in_waiting > 0:
                ser.read()

            # Send command
            ser.write(bytes(test['packet']))
            time.sleep(0.2)  # Wait for response

            # Read response
            response = []
            if ser.in_waiting > 0:
                response = list(ser.read(ser.in_waiting))
                print(f"   Response: {[hex(b) for b in response]}")
                print(f"   Length: {len(response)} bytes (expected: {test['expected_response_length']})")

                # Analyze response
                if len(response) >= 6:
                    if response[0] == 0xFF and response[1] == 0xFF:
                        servo_id = response[2]
                        length = response[3]
                        error = response[4]
                        print(f"   ✅ Valid header, Servo ID: {servo_id}, Length: {length}, Error: {error}")
                    else:
                        print(f"   ❌ Invalid header: {hex(response[0])} {hex(response[1])}")
                else:
                    print(f"   ⚠️ Response too short")
            else:
                print(f"   ❌ NO RESPONSE")
                response = []

            # Store result
            working_communication.append({
                'test': test['name'],
                'sent': test['packet'],
                'received': response,
                'success': len(response) >= test['expected_response_length']
            })

            time.sleep(0.5)

        # Summary
        print(f"\n📊 TEST SUMMARY:")
        print("=" * 30)
        successful_tests = 0
        for comm in working_communication:
            status = "✅ PASS" if comm['success'] else "❌ FAIL"
            print(f"   {comm['test']}: {status}")
            if comm['success']:
                successful_tests += 1

        print(f"\nSuccess rate: {successful_tests}/{len(tests)} tests passed")

        if successful_tests == 0:
            print("\n🚨 CRITICAL: No servo communication working!")
            print("Possible issues:")
            print("- Servo not connected/powered")
            print("- Wrong baud rate")
            print("- Wrong pins")
            print("- Servo ID not 1")
            print("- Hardware failure")
        elif successful_tests < len(tests):
            print("\n⚠️ PARTIAL: Some commands working, others failing")
        else:
            print("\n🎉 SUCCESS: All communication working!")

        ser.close()
        return working_communication

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def test_different_servo_ids():
    """Test if servo is responding on different IDs"""
    print(f"\n🔍 SERVO ID SCAN")
    print("=" * 20)

    try:
        ser = serial.Serial('/dev/ttyACM0', 115200, timeout=1)
        time.sleep(1)

        found_servos = []

        for servo_id in range(1, 16):
            print(f"Testing servo ID {servo_id}...", end=" ")

            # Ping packet for this servo ID
            packet = [0xFF, 0xFF, servo_id, 0x02, 0x01]
            checksum = (~sum(packet[2:])) & 0xFF
            packet.append(checksum)

            # Clear buffer
            while ser.in_waiting > 0:
                ser.read()

            # Send ping
            ser.write(bytes(packet))
            time.sleep(0.1)

            # Check response
            if ser.in_waiting > 0:
                response = list(ser.read(ser.in_waiting))
                if len(response) >= 6 and response[0] == 0xFF and response[1] == 0xFF:
                    print(f"✅ FOUND! Response: {[hex(b) for b in response]}")
                    found_servos.append(servo_id)
                else:
                    print(f"❌ Invalid response: {[hex(b) for b in response]}")
            else:
                print("❌ No response")

        print(f"\nFound servos on IDs: {found_servos}")
        ser.close()
        return found_servos

    except Exception as e:
        print(f"❌ Error: {e}")
        return []

def test_baud_rates():
    """Test different baud rates"""
    print(f"\n🔍 BAUD RATE TEST")
    print("=" * 20)

    baud_rates = [1000000, 500000, 115200, 57600, 9600]
    working_baud = None

    for baud in baud_rates:
        print(f"Testing {baud} baud...", end=" ")

        try:
            ser = serial.Serial('/dev/ttyACM0', baud, timeout=0.5)
            time.sleep(0.2)

            # Simple ping
            packet = [0xFF, 0xFF, 0x01, 0x02, 0x01, 0xFB]

            # Clear buffer
            while ser.in_waiting > 0:
                ser.read()

            ser.write(bytes(packet))
            time.sleep(0.2)

            if ser.in_waiting > 0:
                response = list(ser.read(ser.in_waiting))
                if len(response) >= 6 and response[0] == 0xFF:
                    print(f"✅ WORKING! Response: {[hex(b) for b in response[:6]]}")
                    working_baud = baud
                else:
                    print(f"❌ Bad response: {[hex(b) for b in response]}")
            else:
                print("❌ No response")

            ser.close()

        except Exception as e:
            print(f"❌ Error: {e}")

    print(f"\nWorking baud rate: {working_baud}")
    return working_baud

if __name__ == "__main__":
    # Run comprehensive tests
    print("🔧 SYSTEMATIC SERVO DEBUGGING")
    print("=" * 50)

    # Test 1: Basic communication
    comm_results = capture_communication()

    # Test 2: Try different servo IDs
    found_servos = test_different_servo_ids()

    # Test 3: Try different baud rates
    working_baud = test_baud_rates()

    # Final summary
    print(f"\n🎯 DEBUGGING SUMMARY")
    print("=" * 30)
    print(f"Communication tests passed: {sum(1 for r in comm_results if r['success'])}/{len(comm_results)}")
    print(f"Found servo IDs: {found_servos}")
    print(f"Working baud rate: {working_baud}")

    if not found_servos and not working_baud:
        print("\n🚨 CRITICAL ISSUE: No servo communication detected")
        print("Hardware troubleshooting needed:")
        print("1. Check power to Waveshare adapter")
        print("2. Verify ESP32 ↔ Adapter wiring")
        print("3. Check servo connections")
        print("4. Verify servo power supply")
    elif found_servos:
        print(f"\n✅ SUCCESS: Found working servo(s) on ID(s): {found_servos}")
        print("Use this information to fix firmware servo ID!")
    else:
        print("\n⚠️ PARTIAL: Some communication detected but needs investigation")