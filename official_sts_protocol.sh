#!/bin/bash

echo "🤖 Official STS3032 Protocol Test"
echo "================================="
echo "Based on Feetech official SDK and vassar-robotics/feetech-servo-sdk"

# Function to send STS protocol packet
send_sts_packet() {
    local servo_id=$1
    local instruction=$2
    shift 2
    local params=("$@")

    # Calculate length = instruction + params + checksum
    local length=$((1 + ${#params[@]} + 1))

    # Build packet: FF FF ID LENGTH INSTRUCTION PARAMS... CHECKSUM
    local sum=$((servo_id + length + instruction))
    for param in "${params[@]}"; do
        sum=$((sum + param))
    done
    local checksum=$(((~sum) & 0xFF))

    # Send packet
    printf "\xFF\xFF\x$(printf %02x $servo_id)\x$(printf %02x $length)\x$(printf %02x $instruction)" > /dev/ttyACM0

    for param in "${params[@]}"; do
        printf "\x$(printf %02x $param)" > /dev/ttyACM0
    done

    printf "\x$(printf %02x $checksum)" > /dev/ttyACM0

    echo "Sent STS packet: ID=$servo_id, INST=$instruction, PARAMS=[${params[*]}], CHECKSUM=$checksum"
}

# Function to ping servo (official SDK method)
ping_sts_servo() {
    local servo_id=$1
    echo "Pinging STS servo $servo_id (official protocol)..."

    (
        timeout 2s cat /dev/ttyACM0 > sts_ping_${servo_id}.txt &
        sleep 0.1
        send_sts_packet $servo_id 1  # PING instruction = 1
        sleep 0.5
        wait
    )

    if [ -s sts_ping_${servo_id}.txt ]; then
        echo "  ✅ STS servo $servo_id responded!"
        echo "  Response: $(hexdump -C sts_ping_${servo_id}.txt | head -1)"
        return 0
    else
        echo "  ❌ No response from STS servo $servo_id"
        return 1
    fi
}

# Function to read position (official SDK method)
read_sts_position() {
    local servo_id=$1
    echo "Reading position from STS servo $servo_id..."

    (
        timeout 2s cat /dev/ttyACM0 > sts_pos_${servo_id}.txt &
        sleep 0.1
        # Read instruction (2), address 56 (0x38), length 2
        send_sts_packet $servo_id 2 56 0 2 0
        sleep 0.5
        wait
    )

    if [ -s sts_pos_${servo_id}.txt ]; then
        echo "  📍 Position response from servo $servo_id:"
        hexdump -C sts_pos_${servo_id}.txt | head -2
        return 0
    else
        echo "  ❌ No position response"
        return 1
    fi
}

# Function to write position (official SDK method)
write_sts_position() {
    local servo_id=$1
    local position=$2
    local time_ms=${3:-1000}

    echo "Writing position $position to STS servo $servo_id (time: ${time_ms}ms)..."

    local pos_low=$((position & 0xFF))
    local pos_high=$(((position >> 8) & 0xFF))
    local time_low=$((time_ms & 0xFF))
    local time_high=$(((time_ms >> 8) & 0xFF))

    # Write instruction (3), address 42 (0x2A), data
    send_sts_packet $servo_id 3 42 0 $pos_low $pos_high $time_low $time_high 0 0
}

echo "Testing official STS3032 protocol..."

# Test different baud rates from official SDK
for baud in 1000000 500000 115200; do
    echo ""
    echo "🔧 Testing official STS protocol at $baud baud..."
    stty -F /dev/ttyACM0 $baud cs8 -cstopb -parenb raw -echo

    # Scan for servos using official ping
    found_servos=()
    for servo_id in {1..15}; do
        if ping_sts_servo $servo_id >/dev/null 2>&1; then
            found_servos+=($servo_id)
            echo "✅ Found STS servo ID $servo_id at $baud baud"
        fi
        sleep 0.2
    done

    if [ ${#found_servos[@]} -gt 0 ]; then
        echo ""
        echo "🎯 Found working STS servos: ${found_servos[*]}"
        echo ""

        # Test position reading with official protocol
        echo "📍 Reading positions with official STS protocol..."
        for servo_id in "${found_servos[@]}"; do
            if [ $servo_id -le 4 ]; then
                read_sts_position $servo_id
                sleep 0.3
            fi
        done

        echo ""
        echo "🏃 Testing movement with official STS protocol..."
        for servo_id in "${found_servos[@]}"; do
            if [ $servo_id -le 4 ]; then
                echo "Testing movement on STS servo $servo_id..."

                # Enable torque (write to address 40)
                send_sts_packet $servo_id 3 40 0 1
                sleep 0.5

                # Test positions
                for pos in 1500 2500 2048; do
                    write_sts_position $servo_id $pos 1000
                    sleep 2
                    read_sts_position $servo_id
                    sleep 0.5
                done
            fi
        done

        echo ""
        echo "✅ Official STS protocol test complete at $baud baud!"
        break
    else
        echo "❌ No STS servos found at $baud baud"
    fi
done

echo ""
echo "🎯 Official STS3032 protocol test finished!"
echo "If servos moved, the official protocol is working!"

# Sources used:
echo ""
echo "Based on official sources:"
echo "- vassar-robotics/feetech-servo-sdk"
echo "- matthieuvigne/STS_servos Arduino library"
echo "- Feetech official SMS1.0 protocol documentation"