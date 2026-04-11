#!/bin/bash
# Manual firmware flashing using PlatformIO's esptool

echo "🚀 PhoneWalker Manual Flash"
echo "==========================="

echo "📋 MANUAL FLASHING INSTRUCTIONS:"
echo ""
echo "1. Fix permissions (run in terminal):"
echo "   sudo chmod 666 /dev/ttyACM0"
echo ""
echo "2. Flash with PlatformIO esptool:"
echo "   cd firmware"
echo "   ~/.platformio/packages/tool-esptoolpy/esptool.py --chip esp32s3 --port /dev/ttyACM0 --baud 460800 write_flash -z 0x1000 .pio/build/esp32-s3-devkitc-1/bootloader.bin 0x8000 .pio/build/esp32-s3-devkitc-1/partitions.bin 0x10000 .pio/build/esp32-s3-devkitc-1/firmware.bin"
echo ""
echo "3. Monitor output:"
echo "   pio device monitor --baud 115200"
echo ""
echo "🎯 OR try simplified upload:"
echo "   cd firmware && pio run -e esp32-s3-devkitc-1 -t upload"
echo ""

echo "✅ Firmware binary ready at: firmware/.pio/build/esp32-s3-devkitc-1/firmware.bin"
ls -la firmware/.pio/build/esp32-s3-devkitc-1/firmware.*