#!/bin/bash

echo "PhoneWalker Quick Servo Test"
echo "============================"

# Check if device exists
if [ ! -e "/dev/ttyACM0" ]; then
    echo "❌ Device /dev/ttyACM0 not found"
    exit 1
fi

echo "✅ Serial device found: /dev/ttyACM0"

# Check device info
echo "📱 Device info:"
udevadm info -q property -n /dev/ttyACM0 | grep -E "ID_VENDOR|ID_MODEL|ID_SERIAL" | head -3

echo ""
echo "🔧 Setting up serial port..."

# Try to configure serial port (this will show if we have permission)
if stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb 2>/dev/null; then
    echo "✅ Serial port configured (1000000 baud, 8N1)"

    echo ""
    echo "📡 Testing servo communication..."

    # Create ping packet for servo ID 1: FF FF 01 02 01 FB
    # This is a STS3032 ping command
    printf "\xFF\xFF\x01\x02\x01\xFB" > /dev/ttyACM0 2>/dev/null

    if [ $? -eq 0 ]; then
        echo "✅ Ping packet sent to servo ID 1"

        # Try to read response
        echo "🔍 Waiting for response..."
        timeout 1s dd if=/dev/ttyACM0 bs=1 count=10 2>/dev/null | xxd

        if [ $? -eq 0 ]; then
            echo "📥 Response received (see hex dump above)"
        else
            echo "❌ No response from servo"
        fi
    else
        echo "❌ Failed to send ping packet"
    fi

else
    echo "❌ Cannot configure serial port"
    echo "💡 Solution: Run this command first:"
    echo "   sudo usermod -a -G dialout $USER"
    echo "   Then logout and login again"
    echo ""
    echo "🔧 Or run with sudo:"
    echo "   sudo ./quick_servo_test.sh"
fi

echo ""
echo "🔋 Power Supply Check:"
echo "   - STS3032 servos need 6.0V - 8.4V"
echo "   - Each servo: up to 3A peak current"
echo "   - 15 servos: need 30-45A total!"
echo "   - USB power (5V/0.5A) is NOT enough"
echo ""
echo "🚨 Red blinking LED means:"
echo "   - Insufficient power supply"
echo "   - Communication timeout"
echo "   - Overload condition"
echo "   - Wrong servo ID"