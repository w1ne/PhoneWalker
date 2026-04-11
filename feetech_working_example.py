#!/usr/bin/env python3
"""
Working STS3032 example based on official Feetech SDK
Based on vassar-robotics/feetech-servo-sdk and matthieuvigne/STS_servos
"""

import serial
import time

class STS3032Controller:
    """STS3032 controller based on official SDK protocol"""

    def __init__(self, port='/dev/ttyACM0', baudrate=1000000):
        self.serial = serial.Serial(port, baudrate, timeout=1)
        time.sleep(0.1)

    def checksum(self, packet):
        """Calculate checksum for STS protocol"""
        return (~sum(packet[2:-1])) & 0xFF

    def send_packet(self, servo_id, instruction, params=None):
        """Send packet using STS protocol"""
        if params is None:
            params = []

        length = len(params) + 2  # instruction + checksum
        packet = [0xFF, 0xFF, servo_id, length, instruction] + params
        packet.append(self.checksum(packet))

        self.serial.write(bytes(packet))
        print(f"Sent: {[hex(b) for b in packet]}")
        return packet

    def read_response(self):
        """Read response from servo"""
        time.sleep(0.05)
        if self.serial.in_waiting > 0:
            response = self.serial.read(self.serial.in_waiting)
            return list(response)
        return None

    def ping(self, servo_id):
        """Ping servo - official SDK method"""
        print(f"Pinging servo {servo_id}...")
        self.send_packet(servo_id, 0x01)  # PING instruction

        response = self.read_response()
        if response and len(response) >= 6:
            if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                print(f"  ✅ Servo {servo_id} responded!")
                if len(response) >= 5:
                    error = response[4]
                    if error == 0:
                        print(f"    No errors")
                    else:
                        print(f"    Error code: 0x{error:02X}")
                return True

        print(f"  ❌ No response from servo {servo_id}")
        return False

    def read_position(self, servo_id):
        """Read current position - SMS1.0 protocol"""
        print(f"Reading position from servo {servo_id}...")

        # Read instruction (0x02) from address 56 (0x38) - Present Position, 2 bytes
        params = [56, 0, 2, 0]  # addr_low, addr_high, length_low, length_high
        self.send_packet(servo_id, 0x02, params)

        response = self.read_response()
        if response and len(response) >= 7:
            if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                pos_low = response[5]
                pos_high = response[6]
                position = pos_low | (pos_high << 8)
                print(f"  📍 Position: {position}")
                return position

        print(f"  ❌ Failed to read position")
        return None

    def write_position(self, servo_id, position, time_ms=1000):
        """Write position - based on official SDK"""
        print(f"Moving servo {servo_id} to position {position} (time: {time_ms}ms)")

        # Write instruction (0x03) to address 42 (0x2A) - Goal Position
        pos_low = position & 0xFF
        pos_high = (position >> 8) & 0xFF
        time_low = time_ms & 0xFF
        time_high = (time_ms >> 8) & 0xFF

        params = [42, 0, pos_low, pos_high, time_low, time_high, 0, 0]  # addr_low, addr_high, data...
        self.send_packet(servo_id, 0x03, params)

        response = self.read_response()
        if response and len(response) >= 6:
            if response[0] == 0xFF and response[1] == 0xFF and response[2] == servo_id:
                print(f"  ✅ Position command sent successfully")
                return True

        print(f"  ❌ Failed to set position")
        return False

    def enable_torque(self, servo_id, enable=True):
        """Enable/disable torque"""
        print(f"{'Enabling' if enable else 'Disabling'} torque for servo {servo_id}")

        # Write to address 40 (0x28) - Torque Enable
        params = [40, 0, 1 if enable else 0]
        self.send_packet(servo_id, 0x03, params)

        response = self.read_response()
        return response is not None

def main():
    """Test STS3032 servos with official protocol"""
    print("🤖 STS3032 Official SDK Test")
    print("============================")
    print("Based on vassar-robotics/feetech-servo-sdk")

    try:
        # Test different baud rates from official SDK
        for baud in [1000000, 500000, 115200]:
            print(f"\n🔧 Testing at {baud} baud...")

            controller = STS3032Controller(baudrate=baud)

            # Scan for servos
            found_servos = []
            for servo_id in range(1, 16):
                if controller.ping(servo_id):
                    found_servos.append(servo_id)
                time.sleep(0.1)

            if found_servos:
                print(f"\n🎯 Found servos at {baud} baud: {found_servos}")

                # Test position reading first
                print(f"\n📍 Reading positions...")
                for servo_id in found_servos[:4]:  # Test first 4
                    position = controller.read_position(servo_id)
                    time.sleep(0.2)

                # Test movement
                print(f"\n🏃 Testing movement...")
                for servo_id in found_servos[:4]:
                    # Enable torque
                    controller.enable_torque(servo_id, True)
                    time.sleep(0.2)

                    # Test positions
                    for pos in [1500, 2500, 2048]:
                        controller.write_position(servo_id, pos, 1000)
                        time.sleep(2)
                        # Read back position
                        controller.read_position(servo_id)
                        time.sleep(0.5)

                controller.serial.close()
                print(f"\n✅ Success! Servos working at {baud} baud")
                return

            controller.serial.close()
            print(f"❌ No servos found at {baud} baud")

    except Exception as e:
        print(f"Error: {e}")

    print("\n❌ No working servo communication found")

if __name__ == "__main__":
    main()