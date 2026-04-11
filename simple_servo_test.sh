#!/bin/bash

echo "🤖 PhoneWalker Simple Servo Test"
echo "==============================="

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

echo "📡 Testing servo ID 1..."

# Send ping to servo ID 1: FF FF 01 02 01 FB
echo -e -n "\xFF\xFF\x01\x02\x01\xFB" > /dev/ttyACM0
echo "✅ Ping sent to servo ID 1"

# Read response
echo "👂 Reading response..."
timeout 1s cat /dev/ttyACM0 | xxd -l 20

echo ""
echo "📡 Testing servo ID 2..."

# Send ping to servo ID 2: FF FF 02 02 01 FA
echo -e -n "\xFF\xFF\x02\x02\x01\xFA" > /dev/ttyACM0
echo "✅ Ping sent to servo ID 2"

# Read response
echo "👂 Reading response..."
timeout 1s cat /dev/ttyACM0 | xxd -l 20

echo ""
echo "🔍 Analysis:"
echo "  - If you see 'ffff...' responses = Servos are working!"
echo "  - If no response = Check servo power or IDs"
echo "  - Constant red LED = Normal standby mode"

echo ""
echo "🚀 Next steps:"
echo "  1. Install development tools: sudo apt install python3-pip && pip3 install platformio"
echo "  2. Upload full firmware: cd ~/projects/PhoneWalker/firmware && pio run --target upload"
echo "  3. Test walking: pio device monitor (then type 'standup' and 'walk 3')"