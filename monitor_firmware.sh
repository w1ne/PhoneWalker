#!/bin/bash
# Monitor PhoneWalker firmware output

echo "📺 PhoneWalker Firmware Monitor"
echo "==============================="
echo "Press Ctrl+C to exit"
echo ""

# Check if device exists
if [ ! -e /dev/ttyACM0 ]; then
    echo "❌ ESP32 not found at /dev/ttyACM0"
    echo "   Check USB connection"
    exit 1
fi

echo "🔌 Connecting to ESP32 at 115200 baud..."
echo "📋 Expected commands:"
echo "   t = Transparent mode"
echo "   d = Start dancing"
echo "   s = Stop dancing"
echo "   p = Ping test"
echo "   r = Read positions"
echo "   h = Help"
echo ""

# Try to monitor with different tools
if command -v pio &> /dev/null; then
    echo "Using PlatformIO monitor..."
    cd firmware && pio device monitor --baud 115200
elif command -v picocom &> /dev/null; then
    echo "Using picocom..."
    picocom /dev/ttyACM0 -b 115200
elif command -v screen &> /dev/null; then
    echo "Using screen..."
    screen /dev/ttyACM0 115200
else
    echo "❌ No serial monitor tool found"
    echo "   Install picocom or screen:"
    echo "   sudo apt install picocom"
fi