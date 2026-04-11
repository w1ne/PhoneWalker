#!/bin/bash

echo "🤖 PhoneWalker Direct Servo Control"
echo "=================================="
echo "USB-UART Bridge → STS3032 Servos"
echo ""

# Configure serial port
stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

# Function to send servo command
send_servo_cmd() {
    local id=$1
    local position=$2
    local time=${3:-1000}  # Default 1 second

    echo "Moving servo $id to position $position (time: ${time}ms)"

    # STS3032 position command: FF FF ID LEN INSTRUCTION POS_L POS_H TIME_L TIME_H SPEED_L SPEED_H CHECKSUM
    local pos_l=$((position & 0xFF))
    local pos_h=$(((position >> 8) & 0xFF))
    local time_l=$((time & 0xFF))
    local time_h=$(((time >> 8) & 0xFF))

    # Calculate checksum
    local checksum=$(( (~(id + 7 + 3 + pos_l + pos_h + time_l + time_h + 0 + 0)) & 0xFF ))

    # Send command
    printf "\xFF\xFF\x$(printf %02x $id)\x07\x03\x$(printf %02x $pos_l)\x$(printf %02x $pos_h)\x$(printf %02x $time_l)\x$(printf %02x $time_h)\x00\x00\x$(printf %02x $checksum)" > /dev/ttyACM0
}

# Function to ping servo
ping_servo() {
    local id=$1
    echo "Pinging servo $id..."

    local checksum=$(( (~(id + 2 + 1)) & 0xFF ))
    printf "\xFF\xFF\x$(printf %02x $id)\x02\x01\x$(printf %02x $checksum)" > /dev/ttyACM0

    sleep 0.1
    if timeout 0.5s cat /dev/ttyACM0 | xxd -l 20 | grep -q "ffff"; then
        echo "✅ Servo $id responded!"
        return 0
    else
        echo "❌ No response from servo $id"
        return 1
    fi
}

# Function to scan for servos
scan_servos() {
    echo "🔍 Scanning for servos..."
    found_servos=()

    for id in {1..15}; do
        if ping_servo $id >/dev/null 2>&1; then
            found_servos+=($id)
            echo "  ✅ Found servo ID $id"
        fi
    done

    echo "Found servos: ${found_servos[*]}"
}

# Function to stand up (center all servos)
standup() {
    echo "🚶 Standing up robot..."

    for id in 1 2 3 4; do
        send_servo_cmd $id 2048 1000  # Center position
        sleep 0.2
    done

    echo "✅ Robot standing!"
}

# Function to walk forward
walk_forward() {
    local steps=${1:-1}
    echo "🚶 Walking forward $steps steps..."

    for ((step=1; step<=steps; step++)); do
        echo "Step $step:"

        # Lift front-left and back-right
        send_servo_cmd 1 1800 300    # Front-left up
        send_servo_cmd 4 1800 300    # Back-right up
        sleep 0.4

        # Move forward and back
        send_servo_cmd 1 1800 200    # Front-left forward
        send_servo_cmd 4 1800 200    # Back-right forward
        send_servo_cmd 2 2300 400    # Front-right back
        send_servo_cmd 3 2300 400    # Back-left back
        sleep 0.5

        # Lower lifted legs
        send_servo_cmd 1 2048 200    # Front-left down
        send_servo_cmd 4 2048 200    # Back-right down
        sleep 0.3

        # Lift front-right and back-left
        send_servo_cmd 2 1800 300    # Front-right up
        send_servo_cmd 3 1800 300    # Back-left up
        sleep 0.4

        # Move forward and back
        send_servo_cmd 2 1800 200    # Front-right forward
        send_servo_cmd 3 1800 200    # Back-left forward
        send_servo_cmd 1 2300 400    # Front-left back
        send_servo_cmd 4 2300 400    # Back-right back
        sleep 0.5

        # Lower lifted legs
        send_servo_cmd 2 2048 200    # Front-right down
        send_servo_cmd 3 2048 200    # Back-left down
        sleep 0.3
    done

    echo "✅ Walk complete!"
}

# Main menu
while true; do
    echo ""
    echo "Commands:"
    echo "  scan     - Scan for servos"
    echo "  ping <id> - Ping specific servo"
    echo "  move <id> <pos> [time] - Move servo to position"
    echo "  standup  - Stand up robot"
    echo "  walk [steps] - Walk forward"
    echo "  quit     - Exit"
    echo ""

    read -p "PhoneWalker> " cmd args

    case $cmd in
        "scan")
            scan_servos
            ;;
        "ping")
            if [ -n "$args" ]; then
                ping_servo $args
            else
                echo "Usage: ping <servo_id>"
            fi
            ;;
        "move")
            read -a params <<< "$args"
            if [ ${#params[@]} -ge 2 ]; then
                send_servo_cmd ${params[0]} ${params[1]} ${params[2]:-1000}
            else
                echo "Usage: move <servo_id> <position> [time_ms]"
            fi
            ;;
        "standup")
            standup
            ;;
        "walk")
            walk_forward ${args:-1}
            ;;
        "quit"|"exit"|"q")
            echo "Goodbye!"
            exit 0
            ;;
        *)
            echo "Unknown command: $cmd"
            ;;
    esac
done