#!/bin/bash

echo "📍 SCServo Library Working Example"
echo "Based on actual SCServo-Arduino library"

# Configure for SCServo protocol
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

echo "Testing with exact SCServo library protocol..."

# Function to send exact SCServo read command
scservo_read_position() {
    local id=$1

    echo "Reading position from servo $id using SCServo lib format..."

    # SCServo library format for position read
    # SMS_STS.ReadPos(id) sends: FF FF id 04 02 38 00 02 checksum
    local checksum=$(( (~(id + 4 + 2 + 0x38 + 0 + 2)) & 0xFF ))

    (
        # Monitor response
        timeout 2s cat /dev/ttyACM0 > servo${id}_pos.txt &

        # Send exact command from SCServo library
        printf "\xFF\xFF\x$(printf %02x $id)\x04\x02\x38\x00\x02\x$(printf %02x $checksum)" > /dev/ttyACM0

        sleep 0.5
        wait
    )

    if [ -s servo${id}_pos.txt ]; then
        echo "  ✅ Got response from servo $id:"
        hexdump -C servo${id}_pos.txt

        # Decode position if response is valid
        local response=$(xxd -p servo${id}_pos.txt | tr -d '\n')
        if [[ $response == ffff* ]]; then
            echo "  📍 Valid position response detected"
        fi
    else
        echo "  ❌ No response from servo $id"
    fi
}

# Test with different baud rates from SCServo examples
for baud in 1000000 500000; do
    echo ""
    echo "Testing SCServo at $baud baud (library standard)..."
    stty -F /dev/ttyACM0 $baud

    # Test servo IDs 1-4
    for id in 1 2 3 4; do
        scservo_read_position $id
        sleep 0.2
    done

    # Check if we got any responses
    if ls servo*_pos.txt 2>/dev/null | xargs -r cat | grep -q .; then
        echo "✅ Found working servos at $baud baud!"
        break
    fi
done

# Also try Feetech SCS library format
echo ""
echo "Trying Feetech SCS library format..."
stty -F /dev/ttyACM0 1000000

for id in 1 2 3 4; do
    echo "SCS format read servo $id..."

    # SCS library position read: different address
    local checksum=$(( (~(id + 4 + 2 + 0x26 + 0 + 2)) & 0xFF ))

    (
        timeout 1s cat /dev/ttyACM0 > scs${id}_pos.txt &
        printf "\xFF\xFF\x$(printf %02x $id)\x04\x02\x26\x00\x02\x$(printf %02x $checksum)" > /dev/ttyACM0
        wait
    )

    if [ -s scs${id}_pos.txt ]; then
        echo "  ✅ SCS response from servo $id"
        hexdump -C scs${id}_pos.txt | head -2
    fi

    sleep 0.2
done

echo ""
echo "📊 Summary:"
echo "If any responses above, communication is working!"
echo "If all empty, fundamental communication problem."