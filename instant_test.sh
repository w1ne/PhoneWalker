#!/bin/bash

echo "🤖 PhoneWalker Instant Servo Test"
echo "================================="

# Quick servo ping using basic tools
echo "📡 Sending ping to servo ID 1..."

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb 2>/dev/null

# Send ping packet: FF FF 01 02 01 FB
printf "\xFF\xFF\x01\x02\x01\xFB" > /dev/ttyACM0

echo "✅ Ping sent!"

# Read response
echo "👂 Reading response..."
timeout 1s dd if=/dev/ttyACM0 bs=1 count=10 2>/dev/null | xxd -p

echo ""
echo "🔍 Response analysis:"
echo "  - Empty = No communication"
echo "  - 'ffff...' = Valid servo response"
echo "  - Other = Check wiring/power"