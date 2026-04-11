#!/bin/bash

echo "🤖 PhoneWalker Direct Servo Test"
echo "==============================="

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

echo "📡 Scanning for servos..."

# Test servos 1-4
for id in 1 2 3 4; do
    echo -n "Testing servo $id: "

    # Send ping: FF FF ID 02 01 CHECKSUM
    checksum=$(( (~(id + 2 + 1)) & 0xFF ))
    printf "\xFF\xFF\x$(printf %02x $id)\x02\x01\x$(printf %02x $checksum)" > /dev/ttyACM0

    # Check for response
    sleep 0.1
    response=$(timeout 0.5s dd if=/dev/ttyACM0 bs=1 count=20 2>/dev/null | xxd -p)

    if [[ "$response" == *"ffff"* ]]; then
        echo "FOUND! ✅"
    else
        echo "No response ❌"
    fi

    sleep 0.2
done

echo ""
echo "🎯 Testing servo movement..."

# Move servo 1 to different positions
for pos in 1500 2048 2500 2048; do
    echo "Moving servo 1 to position $pos..."

    pos_l=$((pos & 0xFF))
    pos_h=$(((pos >> 8) & 0xFF))
    checksum=$(( (~(1 + 7 + 3 + pos_l + pos_h + 232 + 3 + 0 + 0)) & 0xFF ))

    printf "\xFF\xFF\x01\x07\x03\x$(printf %02x $pos_l)\x$(printf %02x $pos_h)\xE8\x03\x00\x00\x$(printf %02x $checksum)" > /dev/ttyACM0

    echo "  Position command sent, waiting 2 seconds..."
    sleep 2
done

echo ""
echo "✅ Test complete!"
echo "💡 If you saw servo responses and movement, everything is working!"
echo "💡 Red LEDs should turn green during movement"