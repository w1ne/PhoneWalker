#!/usr/bin/env python3
"""
📊 Servo Position Monitor & Collaboration System
Track actual servo positions and enable coordinated movement
"""

import serial
import time
import json
from datetime import datetime

class ServoMonitor:
    def __init__(self, port='/dev/ttyACM0', baud=115200):
        self.ser = serial.Serial(port, baud, timeout=1)
        self.servos = {}  # Track servo states
        time.sleep(1)

    def send_command(self, servo_id, instruction, params):
        """Send command and return response"""
        length = len(params) + 2
        packet = [0xFF, 0xFF, servo_id, length, instruction] + params
        checksum = (~sum(packet[2:])) & 0xFF
        packet.append(checksum)

        self.ser.write(bytes(packet))
        time.sleep(0.1)

        if self.ser.in_waiting > 0:
            response = self.ser.read(self.ser.in_waiting)
            return list(response)
        return None

    def read_position(self, servo_id):
        """Read current servo position"""
        # Read instruction: 0x02, Address 56 (Present Position), Length 2
        params = [56, 0, 2, 0]
        response = self.send_command(servo_id, 0x02, params)

        if response and len(response) >= 7:
            pos = response[5] | (response[6] << 8)
            return pos
        return None

    def read_servo_status(self, servo_id):
        """Read comprehensive servo status"""
        status = {
            'id': servo_id,
            'timestamp': datetime.now().isoformat(),
            'position': None,
            'moving': None,
            'load': None,
            'voltage': None,
            'temperature': None,
            'online': False
        }

        # Try to ping servo first
        ping_response = self.send_command(servo_id, 0x01, [])
        if not ping_response or len(ping_response) < 6:
            return status

        status['online'] = True

        # Read position
        status['position'] = self.read_position(servo_id)

        # Read other status (if servo supports it)
        # Moving flag (address 46)
        moving_resp = self.send_command(servo_id, 0x02, [46, 0, 1, 0])
        if moving_resp and len(moving_resp) >= 6:
            status['moving'] = bool(moving_resp[5])

        return status

    def scan_servos(self, max_id=15):
        """Scan for all available servos"""
        print("🔍 Scanning for servos...")
        found_servos = []

        for servo_id in range(1, max_id + 1):
            print(f"Testing servo {servo_id}...", end=" ")
            status = self.read_servo_status(servo_id)

            if status['online']:
                found_servos.append(servo_id)
                self.servos[servo_id] = status
                print(f"✅ Found! Position: {status['position']}")
            else:
                print("❌")

            time.sleep(0.1)

        print(f"\n📊 Found {len(found_servos)} servos: {found_servos}")
        return found_servos

    def monitor_positions(self, servo_ids, duration=10):
        """Monitor servo positions in real-time"""
        print(f"📈 Monitoring positions for {duration}s...")
        print("Time      | " + " | ".join([f"Servo {id:2d}" for id in servo_ids]))
        print("-" * (10 + len(servo_ids) * 12))

        start_time = time.time()
        while time.time() - start_time < duration:
            timestamp = time.strftime("%H:%M:%S")
            positions = []

            for servo_id in servo_ids:
                pos = self.read_position(servo_id)
                positions.append(f"{pos:4d}" if pos is not None else " N/A")

            print(f"{timestamp} | " + " | ".join([f"   {pos}" for pos in positions]))
            time.sleep(0.5)

    def move_servo_to_position(self, servo_id, position, time_ms=1000):
        """Move servo to position and track the movement"""
        print(f"🎯 Moving servo {servo_id} to {position}")

        # Get current position
        current_pos = self.read_position(servo_id)
        if current_pos is not None:
            print(f"   Current position: {current_pos}")

        # Send move command
        pos_l = position & 0xFF
        pos_h = (position >> 8) & 0xFF
        time_l = time_ms & 0xFF
        time_h = (time_ms >> 8) & 0xFF

        params = [42, 0, pos_l, pos_h, time_l, time_h, 0, 0]
        self.send_command(servo_id, 0x03, params)

        # Monitor movement
        print(f"   Monitoring movement...")
        for i in range(10):
            time.sleep(time_ms / 10000.0)
            pos = self.read_position(servo_id)
            if pos is not None:
                print(f"   Progress: {pos}")

        final_pos = self.read_position(servo_id)
        print(f"   Final position: {final_pos}")
        return final_pos

    def coordinated_movement(self, moves):
        """Coordinate multiple servo movements"""
        print("🎭 Coordinated movement sequence:")

        for i, move_set in enumerate(moves):
            print(f"\nStep {i+1}: {move_set.get('name', f'Move {i+1}')}")

            # Send all commands simultaneously
            for servo_id, position in move_set['positions'].items():
                time_ms = move_set.get('time', 1000)
                print(f"  Servo {servo_id} → {position}")

                pos_l = position & 0xFF
                pos_h = (position >> 8) & 0xFF
                time_l = time_ms & 0xFF
                time_h = (time_ms >> 8) & 0xFF

                params = [42, 0, pos_l, pos_h, time_l, time_h, 0, 0]
                self.send_command(servo_id, 0x03, params)

            # Monitor all servos
            wait_time = move_set.get('time', 1000) / 1000.0 + 0.5
            time.sleep(wait_time)

            # Report final positions
            for servo_id in move_set['positions'].keys():
                final_pos = self.read_position(servo_id)
                print(f"  Servo {servo_id} final: {final_pos}")

    def close(self):
        """Close serial connection"""
        self.ser.close()

def main():
    """Main monitoring function"""
    try:
        monitor = ServoMonitor()

        # Scan for servos
        servos = monitor.scan_servos()

        if not servos:
            print("❌ No servos found!")
            return

        print("\n📋 Available commands:")
        print("1. Monitor positions")
        print("2. Test coordinated movement")
        print("3. Individual servo control")

        # For now, let's do a quick demo
        print("\n🎯 Demo: Coordinated Movement Test")

        # Define some coordinated moves
        coord_moves = [
            {
                'name': 'Center Position',
                'positions': {servos[0]: 2048},
                'time': 1000
            },
            {
                'name': 'Left Swing',
                'positions': {servos[0]: 1500},
                'time': 800
            },
            {
                'name': 'Right Swing',
                'positions': {servos[0]: 2500},
                'time': 800
            },
            {
                'name': 'Return to Center',
                'positions': {servos[0]: 2048},
                'time': 1000
            }
        ]

        monitor.coordinated_movement(coord_moves)

        # Monitor positions for a bit
        print("\n📈 Final position monitoring:")
        monitor.monitor_positions(servos, duration=5)

        monitor.close()

    except Exception as e:
        print(f"❌ Monitor error: {e}")

if __name__ == "__main__":
    main()