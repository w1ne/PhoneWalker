#!/bin/bash

echo "🤖 PhoneWalker Servo Response Capture"
echo "===================================="

# Configure serial port
stty -F /dev/ttyACM0 115200 cs8 -cstopb -parenb

echo "📡 Testing servo communication with better capture..."

# Test 1: Send ping and capture response properly
echo "Test 1: Servo ping test"
(
    # Send ping command
    printf "\xFF\xFF\x01\x02\x01\xFB" > /dev/ttyACM0 &

    # Capture response
    sleep 0.2
    timeout 2s cat /dev/ttyACM0 | hexdump -C
)

echo ""
echo "Test 2: Position read test"
(
    # Send position read command
    printf "\xFF\xFF\x01\x04\x02\x26\x02\xCE" > /dev/ttyACM0 &

    # Capture response
    sleep 0.2
    timeout 2s cat /dev/ttyACM0 | hexdump -C
)

echo ""
echo "Test 3: Scan multiple servos"
for id in 1 2 3 4; do
    echo "Testing servo ID $id:"

    # Calculate checksum: ~(ID + 2 + 1) & 0xFF
    case $id in
        1) checksum="FB" ;;
        2) checksum="FA" ;;
        3) checksum="F9" ;;
        4) checksum="F8" ;;
    esac

    (
        printf "\xFF\xFF\x0${id}\x02\x01\x${checksum}" > /dev/ttyACM0 &
        sleep 0.1
        timeout 1s cat /dev/ttyACM0 | hexdump -C | head -2
    )
    echo ""
done

echo "✅ If you see hex data above, servos are definitely working!"
echo "📝 Next: Create proper servo control commands"