#!/bin/bash

echo "🤖 Working SCServo STS3032 Example"
echo "================================="
echo "Based on actual working SCServo protocol"

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

# Function to send SCServo command
send_scservo_cmd() {
    local id=$1
    local instruction=$2
    shift 2
    local params=("$@")

    echo "Sending SCServo command to servo $id, instruction $instruction"

    # Calculate length = instruction + params + checksum
    local length=$((1 + ${#params[@]} + 1))

    # Build packet: FF FF ID LENGTH INSTRUCTION PARAMS... CHECKSUM
    local packet="\xFF\xFF"
    packet+="\x$(printf %02x $id)"
    packet+="\x$(printf %02x $length)"
    packet+="\x$(printf %02x $instruction)"

    # Add parameters
    local sum=$((id + length + instruction))
    for param in "${params[@]}"; do
        packet+="\x$(printf %02x $param)"
        sum=$((sum + param))
    done

    # Calculate checksum
    local checksum=$(((~sum) & 0xFF))
    packet+="\x$(printf %02x $checksum)"

    # Send command
    printf "$packet" > /dev/ttyACM0
    echo "  Packet sent: $packet"
}

# Function to ping servo
ping_scservo() {
    local id=$1
    echo "Pinging SCServo $id..."

    # Ping command: FF FF ID 02 01 CHECKSUM
    local checksum=$(((~(id + 2 + 1)) & 0xFF))
    printf "\xFF\xFF\x$(printf %02x $id)\x02\x01\x$(printf %02x $checksum)" > /dev/ttyACM0

    # Check for response
    sleep 0.2
    local response=$(timeout 0.5s dd if=/dev/ttyACM0 bs=1 count=20 2>/dev/null | xxd -p)

    if [[ -n "$response" ]]; then
        echo "  ✅ Servo $id responded: $response"
        return 0
    else
        echo "  ❌ No response from servo $id"
        return 1
    fi
}

# Function to enable torque
enable_scservo_torque() {
    local id=$1
    local enable=${2:-1}

    echo "Setting torque enable for servo $id to $enable"

    # Write to address 40 (0x28) = Torque Enable
    # Parameters: [addr_l, addr_h, data]
    send_scservo_cmd $id 3 40 0 $enable
    sleep 0.1
}

# Function to set position
set_scservo_position() {
    local id=$1
    local position=$2
    local time_ms=${3:-1000}

    echo "Moving SCServo $id to position $position (time: ${time_ms}ms)"

    # Calculate position bytes
    local pos_l=$((position & 0xFF))
    local pos_h=$(((position >> 8) & 0xFF))
    local time_l=$((time_ms & 0xFF))
    local time_h=$(((time_ms >> 8) & 0xFF))

    # Write to address 42 (0x2A) = Goal Position
    # Parameters: [addr_l, addr_h, pos_l, pos_h, time_l, time_h, speed_l, speed_h]
    send_scservo_cmd $id 3 42 0 $pos_l $pos_h $time_l $time_h 0 0
}

echo "Testing SCServo protocol..."

# Test different baud rates
for baud in 1000000 500000 115200; do
    echo ""
    echo "Testing $baud baud..."
    stty -F /dev/ttyACM0 $baud

    # Scan for servos
    found_servos=()
    for id in {1..15}; do
        if ping_scservo $id >/dev/null 2>&1; then
            found_servos+=($id)
            echo "✅ Found servo ID $id at $baud baud"
        fi
        sleep 0.1
    done

    if [ ${#found_servos[@]} -gt 0 ]; then
        echo "🎯 Found working servos: ${found_servos[*]}"
        echo ""

        # Test movement on found servos
        for servo_id in "${found_servos[@]}"; do
            if [ $servo_id -le 4 ]; then  # Only test first 4
                echo "Testing movement on servo $servo_id..."

                # Enable torque
                enable_scservo_torque $servo_id 1
                sleep 0.5

                # Test positions
                for pos in 1500 2500 2048; do
                    set_scservo_position $servo_id $pos 1000
                    sleep 2
                done

                echo "  Movement test complete for servo $servo_id"
                echo ""
            fi
        done

        echo "✅ SCServo protocol working at $baud baud!"
        break
    else
        echo "❌ No servos found at $baud baud"
    fi
done

echo ""
echo "🎯 SCServo test complete!"
echo "If servos moved, the protocol is working!"