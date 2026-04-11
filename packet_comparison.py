#!/usr/bin/env python3
"""
Packet Comparison Tool
Compare firmware packets vs Python script packets
"""

import serial
import time

def build_python_packet(servo_id, instruction, params):
    """Build packet exactly like the working Python script"""
    length = len(params) + 2  # params + instruction + checksum
    packet = [0xFF, 0xFF, servo_id, length, instruction] + params
    checksum = (~sum(packet[2:])) & 0xFF  # From ID onwards
    packet.append(checksum)
    return packet

def build_firmware_packet(servo_id, instruction, params):
    """Build packet like our firmware should"""
    length = len(params) + 2  # instruction + checksum
    packet = [0xFF, 0xFF, servo_id, length, instruction] + params

    # Calculate checksum starting from ID (like firmware)
    sum_val = servo_id + length + instruction + sum(params)
    checksum = (~sum_val) & 0xFF
    packet.append(checksum)
    return packet

def compare_packets():
    """Compare packets for common servo commands"""
    print("🔍 PACKET COMPARISON TEST")
    print("=" * 40)

    # Test cases
    test_cases = [
        {
            'name': 'Enable Torque',
            'servo_id': 1,
            'instruction': 0x03,
            'params': [40, 0, 1]  # Address 40, value 1
        },
        {
            'name': 'Move to Center (2048)',
            'servo_id': 1,
            'instruction': 0x03,
            'params': [42, 0, 0, 8, 232, 3, 0, 0]  # Goal position
        },
        {
            'name': 'Move to Left (1500)',
            'servo_id': 1,
            'instruction': 0x03,
            'params': [42, 0, 220, 5, 232, 3, 0, 0]  # 1500 = 0x05DC
        },
        {
            'name': 'Read Position',
            'servo_id': 1,
            'instruction': 0x02,
            'params': [56, 0, 2, 0]  # Address 56, length 2
        }
    ]

    for test in test_cases:
        print(f"\n📋 {test['name']}:")
        print(f"   Servo ID: {test['servo_id']}")
        print(f"   Instruction: 0x{test['instruction']:02X}")
        print(f"   Parameters: {test['params']}")

        # Build packets both ways
        python_packet = build_python_packet(test['servo_id'], test['instruction'], test['params'])
        firmware_packet = build_firmware_packet(test['servo_id'], test['instruction'], test['params'])

        print(f"   Python:   {[hex(b) for b in python_packet]}")
        print(f"   Firmware: {[hex(b) for b in firmware_packet]}")

        # Compare
        if python_packet == firmware_packet:
            print("   ✅ PACKETS MATCH!")
        else:
            print("   ❌ PACKETS DIFFER!")
            # Find differences
            for i, (p, f) in enumerate(zip(python_packet, firmware_packet)):
                if p != f:
                    print(f"      Byte {i}: Python={hex(p)}, Firmware={hex(f)}")

def test_working_python_commands():
    """Test what the working Python script actually sends"""
    print("\n🐍 WORKING PYTHON SCRIPT PACKETS:")
    print("=" * 40)

    # Recreate exact working commands
    commands = [
        {
            'name': 'Enable Torque',
            'packet': [0xFF, 0xFF, 1, 5, 0x03, 40, 0, 1, 0xCD]
        },
        {
            'name': 'Move to 2048',
            'packet': [0xFF, 0xFF, 1, 10, 0x03, 42, 0, 0, 8, 232, 3, 0, 0, 0xD4]
        }
    ]

    for cmd in commands:
        print(f"\n{cmd['name']}:")
        packet = cmd['packet']
        print(f"   Packet: {[hex(b) for b in packet]}")

        # Verify checksum
        checksum_calc = (~sum(packet[2:-1])) & 0xFF
        checksum_actual = packet[-1]

        print(f"   Checksum calc: {hex(checksum_calc)}")
        print(f"   Checksum actual: {hex(checksum_actual)}")

        if checksum_calc == checksum_actual:
            print("   ✅ Checksum correct")
        else:
            print("   ❌ Checksum wrong!")

def create_firmware_test_header():
    """Generate C++ header with correct packet building"""
    print("\n💻 CORRECTED FIRMWARE CODE:")
    print("=" * 40)

    code = '''
// CORRECTED packet building function
void sendServoCommand(int servo_id, uint8_t instruction, uint8_t* params, int param_length) {
  uint8_t length = param_length + 2; // instruction + checksum

  // Build packet array
  uint8_t packet[64];
  int idx = 0;

  packet[idx++] = 0xFF;
  packet[idx++] = 0xFF;
  packet[idx++] = (uint8_t)servo_id;
  packet[idx++] = length;
  packet[idx++] = instruction;

  // Add parameters
  for (int i = 0; i < param_length; i++) {
    packet[idx++] = params[i];
  }

  // Calculate checksum (from ID onwards, excluding header)
  int sum = 0;
  for (int i = 2; i < idx; i++) {
    sum += packet[i];
  }
  packet[idx++] = (~sum) & 0xFF;

  // Send to servo
  SERVO_SERIAL.write(packet, idx);

  // Debug output
  USB_SERIAL.printf("Sent %d bytes: ", idx);
  for (int i = 0; i < idx; i++) {
    USB_SERIAL.printf("%02X ", packet[i]);
  }
  USB_SERIAL.println();
}
'''

    print(code)

if __name__ == "__main__":
    compare_packets()
    test_working_python_commands()
    create_firmware_test_header()