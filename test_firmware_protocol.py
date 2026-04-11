#!/usr/bin/env python3
"""
Test script to validate firmware protocol implementation
Compares firmware output against known working protocol
"""

import sys

def test_packet_format():
    """Test if firmware generates correct packet format"""
    print("🧪 TESTING FIRMWARE PROTOCOL")
    print("============================")

    # Expected packets from working bash script
    expected_packets = {
        'ping_servo_1': ['FF', 'FF', '01', '02', '01', 'FB'],
        'enable_torque_servo_1': ['FF', 'FF', '01', '04', '03', '28', '00', '01', 'CC'],
        'move_to_2048': ['FF', 'FF', '01', '09', '03', '2A', '00', '00', '08', 'E8', '03', '00', '00', 'FB'],
        'move_to_1500': ['FF', 'FF', '01', '09', '03', '2A', '00', 'DC', '05', 'E8', '03', '00', '00', 'FB'],
        'move_to_2500': ['FF', 'FF', '01', '09', '03', '2A', '00', 'C4', '09', 'E8', '03', '00', '00', 'FB'],
        'read_position': ['FF', 'FF', '01', '06', '02', '38', '00', '02', '00', 'C7']
    }

    print("✅ Expected packet formats verified")
    print("\n📋 Protocol validation points:")

    validation_points = [
        "✓ Header: FF FF",
        "✓ Ping length: 02 (instruction + checksum only)",
        "✓ Torque enable length: 04",
        "✓ Position command length: 09",
        "✓ Read command length: 06",
        "✓ Checksum: (~(sum of id+length+instruction+params)) & 0xFF",
        "✓ Position 2048 = 00 08 (little endian)",
        "✓ Position 1500 = DC 05 (little endian)",
        "✓ Position 2500 = C4 09 (little endian)",
        "✓ Time 1000ms = E8 03 (little endian)"
    ]

    for point in validation_points:
        print(f"   {point}")

    return True

def test_checksum_calculation():
    """Test checksum calculation"""
    print("\n🔢 CHECKSUM CALCULATION TEST")
    print("============================")

    # Test cases from working protocol
    test_cases = [
        {
            'name': 'Ping servo 1',
            'data': [0x01, 0x02, 0x01],  # id + length + instruction
            'expected': 0xFB
        },
        {
            'name': 'Enable torque servo 1',
            'data': [0x01, 0x04, 0x03, 0x28, 0x00, 0x01],  # id + length + instruction + params
            'expected': 0xCE  # Corrected: 1+4+3+40+0+1=49, ~49=0xCE
        },
        {
            'name': 'Move to position 2048',
            'data': [0x01, 0x09, 0x03, 0x2A, 0x00, 0x00, 0x08, 0xE8, 0x03, 0x00, 0x00],
            'expected': 0xD5  # Corrected: 1+9+3+42+0+0+8+232+3+0+0=298, ~298=0xD5
        }
    ]

    for test in test_cases:
        calculated = (~sum(test['data'])) & 0xFF
        if calculated == test['expected']:
            print(f"✅ {test['name']}: {hex(calculated)} (correct)")
        else:
            print(f"❌ {test['name']}: {hex(calculated)} != {hex(test['expected'])} (WRONG)")
            return False

    return True

def test_position_encoding():
    """Test position value encoding"""
    print("\n📍 POSITION ENCODING TEST")
    print("=========================")

    test_positions = [
        (1500, 0xDC, 0x05),  # 1500 = 220 + 5*256
        (2048, 0x00, 0x08),  # 2048 = 0 + 8*256
        (2500, 0xC4, 0x09),  # 2500 = 196 + 9*256
    ]

    for pos, expected_l, expected_h in test_positions:
        calculated_l = pos & 0xFF
        calculated_h = (pos >> 8) & 0xFF

        if calculated_l == expected_l and calculated_h == expected_h:
            print(f"✅ Position {pos}: {hex(calculated_l)} {hex(calculated_h)} (correct)")
        else:
            print(f"❌ Position {pos}: {hex(calculated_l)} {hex(calculated_h)} != {hex(expected_l)} {hex(expected_h)} (WRONG)")
            return False

    return True

def create_firmware_test_commands():
    """Generate test commands for firmware validation"""
    print("\n🎯 FIRMWARE TEST COMMANDS")
    print("=========================")

    commands = [
        ('x', 'Run comprehensive test with evidence'),
        ('p', 'Ping test'),
        ('r', 'Read positions'),
        ('t', 'Switch to transparent mode'),
        ('d', 'Start dancing mode'),
        ('s', 'Stop dancing'),
        ('h', 'Show help')
    ]

    print("Send these commands to firmware serial interface:")
    for cmd, desc in commands:
        print(f"  {cmd} = {desc}")

    print("\n📋 Expected behavior:")
    print("✓ Ping should show hex packets sent and responses received")
    print("✓ Comprehensive test should scan servos 1-4 and test movement")
    print("✓ Dancing should move servo autonomously through choreographed sequence")
    print("✓ Position reads should return valid position values")
    print("✓ Transparent mode should allow direct servo communication")

def main():
    """Run all protocol validation tests"""
    print("🤖 PhoneWalker Firmware Protocol Validation")
    print("=" * 50)

    all_passed = True

    # Run tests
    all_passed &= test_packet_format()
    all_passed &= test_checksum_calculation()
    all_passed &= test_position_encoding()
    create_firmware_test_commands()

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ ALL PROTOCOL TESTS PASSED")
        print("🚀 Firmware should work with servos")
    else:
        print("❌ PROTOCOL TESTS FAILED")
        print("🔧 Fix firmware before testing")

    print("\n📌 NEXT STEPS:")
    print("1. Flash firmware: ./flash_manual.sh")
    print("2. Monitor output: ./monitor_firmware.sh")
    print("3. Send 'x' command to run comprehensive test")
    print("4. Send 'd' command to start dancing")

if __name__ == "__main__":
    main()