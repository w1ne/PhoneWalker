#!/bin/bash

echo "🤖 PhoneWalker Detailed Servo Test"
echo "=================================="

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

echo "📡 Testing communication with each servo ID..."

for id in {1..15}; do
    echo -n "Testing ID $id: "

    # Calculate checksum for ping: ~(ID + LENGTH + INSTRUCTION) & 0xFF
    # For ping: LENGTH=2, INSTRUCTION=1
    checksum=$((~(id + 2 + 1) & 0xFF))

    # Send ping packet: FF FF ID 02 01 CHECKSUM
    printf "\xFF\xFF\x%02x\x02\x01\x%02x" $id $checksum > /dev/ttyACM0

    # Wait and read response
    response=$(timeout 0.2s dd if=/dev/ttyACM0 bs=1 count=20 2>/dev/null | xxd -p)

    if [ -n "$response" ]; then
        echo "FOUND! Response: $response"

        # Decode response if it looks valid
        if [[ $response == ffff* ]]; then
            echo "   ✅ Valid servo response"
        fi
    else
        echo "No response"
    fi

    sleep 0.1
done

echo ""
echo "🎯 Testing servo position read..."

# Try to read position from servo ID 1
# Read instruction: FF FF 01 04 02 26 02 CHECKSUM
checksum=$((~(1 + 4 + 2 + 0x26 + 2) & 0xFF))
printf "\xFF\xFF\x01\x04\x02\x26\x02\x%02x" $checksum > /dev/ttyACM0

echo "📍 Position read response:"
timeout 0.5s dd if=/dev/ttyACM0 bs=1 count=20 2>/dev/null | xxd

echo ""
echo "🔴 About the red LEDs:"
echo "   Constant red = Normal standby mode"
echo "   Should turn green when servos move"