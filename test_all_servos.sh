#!/bin/bash

echo "🤖 Testing All Servos - Working Protocol Found!"
echo "=============================================="

stty -F /dev/ttyACM0 1000000 cs8 -cstopb -parenb raw -echo

# Function to send STS packet (proven working)
send_sts_cmd() {
    local id=$1
    local inst=$2
    local p1=${3:-0}
    local p2=${4:-0}
    local p3=${5:-0}
    local p4=${6:-0}
    local p5=${7:-0}
    local p6=${8:-0}
    local p7=${9:-0}
    local p8=${10:-0}

    if [ $inst -eq 1 ]; then
        # PING command
        local checksum=$(( (~(id + 2 + 1)) & 0xFF ))
        printf "\xFF\xFF\x$(printf %02x $id)\x02\x01\x$(printf %02x $checksum)" > /dev/ttyACM0
    elif [ $inst -eq 3 ] && [ $p1 -eq 40 ]; then
        # Enable torque
        local checksum=$(( (~(id + 4 + 3 + 40 + 0 + p3)) & 0xFF ))
        printf "\xFF\xFF\x$(printf %02x $id)\x04\x03\x28\x00\x$(printf %02x $p3)\x$(printf %02x $checksum)" > /dev/ttyACM0
    elif [ $inst -eq 3 ] && [ $p1 -eq 42 ]; then
        # Set position
        local checksum=$(( (~(id + 9 + 3 + 42 + 0 + p3 + p4 + p5 + p6 + p7 + p8)) & 0xFF ))
        printf "\xFF\xFF\x$(printf %02x $id)\x09\x03\x2A\x00\x$(printf %02x $p3)\x$(printf %02x $p4)\x$(printf %02x $p5)\x$(printf %02x $p6)\x$(printf %02x $p7)\x$(printf %02x $p8)\x$(printf %02x $checksum)" > /dev/ttyACM0
    fi
}

echo "🔍 Scanning servos 1-4..."

working_servos=""
for id in 1 2 3 4; do
    echo -n "Servo $id: "

    # Send ping and check response
    timeout 1s cat /dev/ttyACM0 > ping_${id}.txt &
    sleep 0.1
    send_sts_cmd $id 1
    sleep 0.5
    wait

    if [ -s ping_${id}.txt ]; then
        echo "WORKING ✅"
        working_servos="$working_servos $id"
    else
        echo "Not found ❌"
    fi
done

echo ""
echo "Working servos:$working_servos"

if [ -n "$working_servos" ]; then
    echo ""
    echo "🎯 Testing coordinated movement..."

    # Enable torque
    for id in $working_servos; do
        echo "Enabling torque servo $id"
        send_sts_cmd $id 3 40 0 1
        sleep 0.2
    done

    echo ""
    echo "Movement test 1: All to center (2048)"
    for id in $working_servos; do
        send_sts_cmd $id 3 42 0 0 8 232 3 0 0  # pos 2048, time 1000ms
    done
    sleep 3

    echo "Movement test 2: Alternating positions"
    for id in $working_servos; do
        if [ $((id % 2)) -eq 1 ]; then
            echo "  Servo $id to position 1500"
            send_sts_cmd $id 3 42 0 220 5 232 3 0 0  # pos 1500
        else
            echo "  Servo $id to position 2500"
            send_sts_cmd $id 3 42 0 196 9 232 3 0 0  # pos 2500
        fi
    done
    sleep 3

    echo "Movement test 3: Back to center"
    for id in $working_servos; do
        send_sts_cmd $id 3 42 0 0 8 232 3 0 0  # pos 2048
    done
    sleep 2

    echo ""
    echo "✅ All tests complete!"
    echo "📊 Results: Working servos =$working_servos"
else
    echo "❌ No working servos found"
fi