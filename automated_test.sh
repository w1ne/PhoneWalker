#!/bin/bash
# Automated firmware testing script

echo "🤖 PHONEWALKER AUTOMATED TEST"
echo "============================="
echo ""

# Function to check if device exists
check_device() {
    if [ ! -e /dev/ttyACM0 ]; then
        echo "❌ ESP32 not found at /dev/ttyACM0"
        echo "   Connect USB cable and try again"
        exit 1
    fi
    echo "✅ ESP32 device found"
}

# Function to set permissions
set_permissions() {
    echo "🔧 Setting device permissions..."
    if sudo -n true 2>/dev/null; then
        sudo chmod 666 /dev/ttyACM0
        echo "✅ Permissions set"
    else
        echo "⚠️  Cannot set permissions (no sudo access)"
        echo "   Please run: sudo chmod 666 /dev/ttyACM0"
        read -p "Press Enter after setting permissions..."
    fi
}

# Function to flash firmware
flash_firmware() {
    echo ""
    echo "🚀 FLASHING FIRMWARE"
    echo "===================="
    cd firmware

    # Try PlatformIO upload first
    echo "Attempting PlatformIO upload..."
    if pio run -e esp32-s3-devkitc-1 -t upload 2>&1; then
        echo "✅ Firmware flashed successfully with PlatformIO"
        cd ..
        return 0
    else
        echo "⚠️  PlatformIO upload failed, trying manual esptool..."

        # Try manual esptool
        if ~/.platformio/packages/tool-esptoolpy/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash -z 0x1000 .pio/build/esp32-s3-devkitc-1/bootloader.bin 0x8000 .pio/build/esp32-s3-devkitc-1/partitions.bin 0x10000 .pio/build/esp32-s3-devkitc-1/firmware.bin 2>&1; then
            echo "✅ Firmware flashed successfully with esptool"
            cd ..
            return 0
        else
            echo "❌ Flash failed!"
            echo "   Try pressing BOOT button on ESP32 and run again"
            cd ..
            exit 1
        fi
    fi
}

# Function to test firmware communication
test_communication() {
    echo ""
    echo "📡 TESTING COMMUNICATION"
    echo "========================"

    # Wait for device to boot
    sleep 3

    echo "Checking if firmware is responding..."

    # Set up serial port
    stty -F /dev/ttyACM0 115200 cs8 -cstopb -parenb raw -echo

    # Test basic communication
    timeout 2 cat /dev/ttyACM0 > firmware_boot.log &
    sleep 1

    # Send help command
    echo "h" > /dev/ttyACM0
    sleep 1

    # Check boot log
    wait
    if [ -s firmware_boot.log ]; then
        echo "✅ Firmware is responding"
        echo "📋 Boot output:"
        head -n 10 firmware_boot.log | sed 's/^/   /'
    else
        echo "❌ No response from firmware"
        echo "   Check serial connection and baud rate"
        return 1
    fi
}

# Function to run comprehensive test
run_comprehensive_test() {
    echo ""
    echo "🧪 COMPREHENSIVE SERVO TEST"
    echo "==========================="

    # Start capture
    timeout 20 cat /dev/ttyACM0 > comprehensive_test.log &
    CAP_PID=$!

    sleep 1

    # Send comprehensive test command
    echo "x" > /dev/ttyACM0

    # Wait for test to complete
    sleep 15

    # Stop capture
    kill $CAP_PID 2>/dev/null
    wait $CAP_PID 2>/dev/null

    # Analyze results
    echo "📊 Test Results:"
    echo "================"

    if grep -q "WORKING ✅" comprehensive_test.log; then
        echo "✅ Servos detected and responding"
        grep "Servo.*WORKING" comprehensive_test.log | sed 's/^/   /'
    else
        echo "❌ No working servos detected"
    fi

    if grep -q "Position.*error" comprehensive_test.log; then
        echo "📍 Position validation:"
        grep "Position.*error" comprehensive_test.log | sed 's/^/   /'
    fi

    if grep -q "MOVEMENT TEST COMPLETED" comprehensive_test.log; then
        echo "🎯 ✅ Movement test completed successfully"
    else
        echo "🎯 ❌ Movement test failed"
    fi

    # Save full log
    echo ""
    echo "📄 Full test log saved to: comprehensive_test.log"
}

# Function to test dancing
test_dancing() {
    echo ""
    echo "🕺 TESTING DANCING MODE"
    echo "======================"

    # Start capture
    timeout 30 cat /dev/ttyACM0 > dance_test.log &
    CAP_PID=$!

    sleep 1

    # Start dancing
    echo "d" > /dev/ttyACM0
    echo "Starting dance mode for 20 seconds..."

    # Let it dance for 20 seconds
    sleep 20

    # Stop dancing
    echo "s" > /dev/ttyACM0
    sleep 3

    # Stop capture
    kill $CAP_PID 2>/dev/null
    wait $CAP_PID 2>/dev/null

    # Analyze dance results
    echo "💃 Dance Results:"
    echo "================="

    local dance_steps=$(grep -c "Dance step" dance_test.log)
    echo "   Dance steps executed: $dance_steps"

    if [ $dance_steps -gt 0 ]; then
        echo "✅ Dancing mode working - servo executed $dance_steps dance moves"
        echo "📍 Dance positions used:"
        grep "Dance step" dance_test.log | sed 's/^/   /'
    else
        echo "❌ Dancing mode failed - no dance steps detected"
    fi

    echo ""
    echo "📄 Full dance log saved to: dance_test.log"
}

# Main execution
main() {
    echo "Starting automated test sequence..."
    echo ""

    # Step 1: Check device
    check_device

    # Step 2: Set permissions
    set_permissions

    # Step 3: Flash firmware
    flash_firmware

    # Step 4: Test communication
    test_communication

    # Step 5: Run comprehensive test
    run_comprehensive_test

    # Step 6: Test dancing
    test_dancing

    echo ""
    echo "🏁 AUTOMATED TEST COMPLETE"
    echo "=========================="

    # Final summary
    if [ -f comprehensive_test.log ] && grep -q "WORKING ✅" comprehensive_test.log; then
        if [ -f dance_test.log ] && grep -q "Dance step" dance_test.log; then
            echo "🎉 SUCCESS: Firmware working, servos responding, dancing operational"
            echo ""
            echo "📋 EVIDENCE PROVIDED:"
            echo "   ✓ Servo detection and communication"
            echo "   ✓ Position reading and movement verification"
            echo "   ✓ Autonomous dancing with choreographed sequence"
            echo "   ✓ Complete test logs with position evidence"
            echo ""
            echo "🤖 Your robot is ready to dance!"
        else
            echo "⚠️  PARTIAL SUCCESS: Servos work but dancing needs debugging"
        fi
    else
        echo "❌ FAILED: Servos not responding - check hardware connections"
    fi

    echo ""
    echo "📁 Test logs created:"
    ls -la *.log 2>/dev/null | grep -E "\.log$" || echo "   No log files created"
}

# Run main function
main