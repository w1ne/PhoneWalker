#!/bin/bash
# Manual firmware flashing script for PhoneWalker

echo "🚀 PhoneWalker Firmware Flasher"
echo "==============================="

# Check if device is connected
if [ ! -e /dev/ttyACM0 ]; then
    echo "❌ ESP32 not found at /dev/ttyACM0"
    echo "   Check USB connection and try again"
    exit 1
fi

echo "📡 Found ESP32 at /dev/ttyACM0"
echo "🔧 Flashing dancing firmware..."

# Add user to dialout group if needed (requires restart after first time)
if ! groups $USER | grep -q dialout; then
    echo "⚠️  Adding user to dialout group..."
    sudo usermod -a -G dialout $USER
    echo "ℹ️  You may need to logout and login again for group changes to take effect"
fi

# Set permissions temporarily
sudo chmod 666 /dev/ttyACM0

# Flash the firmware
cd firmware
python3 -m esptool --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash -z 0x0 .pio/build/esp32-s3-devkitc-1/firmware.bin

if [ $? -eq 0 ]; then
    echo "✅ Firmware flashed successfully!"
    echo ""
    echo "🎯 FIRMWARE FEATURES:"
    echo "   • 't' = Transparent mode (UART passthrough for debugging)"
    echo "   • 'd' = Start autonomous dancing mode"
    echo "   • 's' = Stop dancing"
    echo "   • 'p' = Ping test"
    echo "   • 'r' = Read servo positions"
    echo "   • 'h' = Help"
    echo ""
    echo "🔌 Connect to serial monitor to see output:"
    echo "   pio device monitor --baud 115200"
else
    echo "❌ Flash failed!"
    echo "   Try pressing BOOT button on ESP32 while flashing"
    exit 1
fi