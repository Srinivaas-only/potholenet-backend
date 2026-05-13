# PotholeNet ESP32-CAM Dual-Mode Detection
## Setup & Deployment Guide

Real-time dashcam detection with automatic reverse/driving mode switching based on GPS velocity.

---

## Table of Contents
1. [Hardware Setup](#hardware-setup)
2. [Software Prerequisites](#software-prerequisites)
3. [Firmware Installation](#firmware-installation)
4. [Configuration](#configuration)
5. [Testing](#testing)
6. [Troubleshooting](#troubleshooting)
7. [API Documentation](#api-documentation)

---

## Hardware Setup

### Components Needed
- **AI Thinker ESP32-CAM** (with USB port)
- **USB Cable** (micro USB)
- **Optional: GPS Module** (NEO-6M with UART output)
- **Optional: OLED Display** (for live status)
- **Micro SD Card** (for video recording - optional)

### Wiring Diagram (GPIO Pins)

```
ESP32-CAM Pin Layout:
                    
          [USB]     <- Micro USB (power + serial)

GPIO Assignments:
- 0  : XCLK (camera clock)
- 4  : Status LED (optional)
- 5  : D0 (camera)
- 16 : GPS RX (if using GPS module)
- 17 : GPS TX (if using GPS module)
- 18 : D1 (camera)
- 19 : D2 (camera)
- 21 : D3 (camera)
- 22 : VSYNC (camera)
- 23 : HSYNC (camera)
- 25 : PCLK (camera)
- 26 : SIOD/SDA (camera I2C)
- 27 : SIOC/SCL (camera I2C)
- 32 : PWDN (power down camera)
- 33 : FLASH LED
- 34 : D4 (camera)
- 35 : D7 (camera)
- 36 : D5 (camera)
- 39 : D6 (camera)
```

### GPS Module Connection (Optional)
If using NEO-6M GPS:
```
NEO-6M    ->  ESP32-CAM
GND       ->  GND
VCC       ->  5V (via 3.3V regulator)
TX        ->  GPIO 16 (RX2)
RX        ->  GPIO 17 (TX2)
```

---

## Software Prerequisites

### 1. Install MicroPython on ESP32-CAM

**Step 1: Install esptool**
```bash
pip install esptool
```

**Step 2: Download MicroPython firmware**
- Download ESP32 MicroPython from: https://micropython.org/download/esp32/
- Get the latest stable version (e.g., `esp32-*.bin`)

**Step 3: Flash MicroPython**
```bash
# Erase flash
esptool.py --chip esp32 --port COM3 erase_flash

# Flash MicroPython (replace with actual filename)
esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 esp32-20230426-v1.20.0.bin
```

Replace `COM3` with your actual USB port:
- **Windows**: COM3, COM4, etc.
- **Linux**: /dev/ttyUSB0, /dev/ttyACM0
- **macOS**: /dev/cu.usbserial-*

### 2. Install ampy (MicroPython File Tool)
```bash
pip install adafruit-ampy
```

---

## Firmware Installation

### Step 1: Update Configuration

Edit `esp32_cam_firmware.py` and set your network details:

```python
# WiFi Configuration
WIFI_SSID = "YOUR_SSID"
WIFI_PASSWORD = "YOUR_PASSWORD"

# Backend Server (your FastAPI)
BACKEND_HOST = "192.168.1.100"  # Change to your server IP
BACKEND_PORT = 8000
```

### Step 2: Upload Firmware

```bash
# Copy firmware to device as main.py (auto-runs on boot)
ampy --port COM3 put esp32_cam_firmware.py main.py

# Or upload both firmware and a helper module
ampy --port COM3 put esp32_cam_firmware.py
```

### Step 3: Verify Upload

```bash
# List files on device
ampy --port COM3 ls

# Expected output:
# boot.py
# main.py  (or esp32_cam_firmware.py)
```

### Step 4: Restart Device

```bash
# Soft reset
ampy --port COM3 run -n << 'EOF'
import machine
machine.soft_reset()
EOF
```

Or manually reset by pressing the RST button on the ESP32-CAM.

---

## Configuration

### WiFi Settings
```python
WIFI_SSID = "YourNetworkName"
WIFI_PASSWORD = "YourPassword"
```

### Backend Server
```python
BACKEND_HOST = "192.168.1.100"      # Your computer/server running FastAPI
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/detect/dual-mode"
```

### Camera Settings
```python
CAMERA_PINS = {
    # Already pre-configured for AI Thinker ESP32-CAM
    # Modify only if using custom board
}

FRAME_INTERVAL = 1.0  # Capture every 1 second
LOCATION_INTERVAL = 5.0  # Update GPS every 5 seconds
```

### GPS Configuration
```python
GPS_UART_NUM = 2       # UART 2 (default for RX2/TX2)
GPS_BAUD = 9600        # Standard GPS baud rate
GPS_RX = 16            # GPIO 16
GPS_TX = 17            # GPIO 17
```

### Detection Modes
The firmware automatically switches modes:
- **REVERSE**: `velocity_kmh < 0` → YOLO-only (fast, <100ms)
- **DRIVING**: `velocity_kmh ≥ 0` → Full detection (accurate, <500ms)

---

## Testing

### 1. Check Serial Output

```bash
# Monitor ESP32 output (use any serial monitor at 115200 baud)
ampy --port COM3 run << 'EOF'
import sys
sys.stdout = machine.UART(0, 115200)
EOF
```

Or use a GUI tool like PuTTY or Arduino IDE Serial Monitor (115200 baud).

### 2. Expected Serial Output

```
[INFO] ==================================================
[INFO] PotholeNet ESP32-CAM Dashboard Camera Starting
[INFO] ==================================================
[INFO] Camera initialized successfully
[INFO] Connecting to YourSSID...
[INFO] Connected! IP: 192.168.1.50
[INFO] Ready for detection. Starting capture loop...
[INFO] Backend: http://192.168.1.100:8000/detect/dual-mode
[DEBUG] Capturing frame 1...
[INFO] Sending frame 1 (65432 bytes, mode=driving, velocity=45.2 km/h)
[INFO] Alert: ⚠️ POTHOLE DETECTED | 🚗 VEHICLE NEARBY (Mode: DRIVING)
[DEBUG] Free memory: 245632 bytes
```

### 3. Test with curl (from your computer)

```bash
# Test dual-mode endpoint with image file
curl -X POST \
  -F "image=@test_image.jpg" \
  -F "mode=driving" \
  -F "velocity_kmh=50.0" \
  http://192.168.1.100:8000/detect/dual-mode

# Expected response:
# {
#   "mode": "DRIVING",
#   "alert": "⚠️ POTHOLE DETECTED | 🚗 VEHICLE NEARBY",
#   "pothole": {"detected": true, "count": 1, "details": [...]},
#   "humans": {"detected": false, "count": 0, "details": []},
#   "vehicles": {"detected": true, "count": 1, "details": [...]},
#   "animals": {"detected": false, "count": 0, "details": []},
#   "velocity_kmh": 50.0
# }
```

### 4. Test Reverse Mode

```bash
# Simulate reverse (negative velocity)
curl -X POST \
  -F "image=@test_image.jpg" \
  -F "mode=reverse" \
  -F "velocity_kmh=-10.0" \
  http://192.168.1.100:8000/detect/dual-mode

# In reverse mode:
# - Pothole detection is SKIPPED (always false)
# - Only YOLO detections returned
# - Response time < 100ms
```

---

## Troubleshooting

### Camera Won't Initialize

**Problem**: `[ERROR] Camera init failed`

**Solutions**:
1. Check GPIO pins match AI Thinker layout
2. Ensure camera module is properly seated
3. Restart ESP32 and try again
4. Check camera module for physical damage

```python
# Diagnostic: Test camera pins individually
import machine
pins_to_test = [0, 5, 18, 19, 21, 22, 23, 25, 26, 27, 32, 34, 35, 36, 39]
for pin in pins_to_test:
    p = machine.Pin(pin, machine.Pin.OUT)
    p.on()
    print(f"Pin {pin}: OK")
    p.off()
```

### WiFi Won't Connect

**Problem**: `[ERROR] WiFi connection timeout`

**Solutions**:
1. Verify SSID and password are correct
2. Check if WiFi 2.4GHz is enabled (ESP32 doesn't support 5GHz)
3. Check distance to router
4. Try manual WiFi connection:

```python
import network
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("SSID", "PASSWORD")
print(wlan.ifconfig())  # Should show IP address
```

### Backend Won't Respond

**Problem**: `[ERROR] HTTP POST error` or `[ERROR] Detection failed`

**Solutions**:
1. Verify backend IP: `ping 192.168.1.100`
2. Check backend is running: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
3. Verify endpoint exists: `curl http://192.168.1.100:8000/docs`
4. Check firewall allows port 8000
5. Monitor backend logs for errors

### Out of Memory

**Problem**: `[ERROR] Memory allocation failed`

**Solutions**:
1. Reduce `FRAME_INTERVAL` to capture less frequently
2. Use lower image quality:
   ```python
   camera.init(..., quality=20)  # Lower = better quality = more memory
   ```
3. Restart device to clear memory leaks

### GPS Data Not Updating

**Problem**: `velocity_kmh` always 0

**Solutions**:
1. Verify GPS module is powered (red LED should be on)
2. Check serial pins (GPIO 16/17) are correct
3. Verify GPS has satellite lock (takes 30-60 seconds)
4. Test GPS directly:

```python
from machine import UART
uart = UART(2, 9600, rx=16, tx=17, timeout=100)
while True:
    if uart.any():
        line = uart.readline()
        print(line)  # Should see NMEA sentences like $GPRMC...
```

---

## API Documentation

### Dual-Mode Detection Endpoint

**URL**: `POST /detect/dual-mode`

**Parameters**:
| Parameter | Type | Required | Range | Description |
|-----------|------|----------|-------|-------------|
| `image` | File (JPEG/PNG) | ✓ | - | Camera frame image |
| `mode` | String | ✗ | `reverse`, `driving` | Detection mode (default: driving) |
| `velocity_kmh` | Float | ✗ | -150 to 250 | Vehicle velocity (negative = reverse) |

**Response**:
```json
{
  "mode": "DRIVING",
  "alert": "⚠️ POTHOLE DETECTED | 🚗 VEHICLE NEARBY",
  "pothole": {
    "detected": true,
    "count": 1,
    "details": [
      {
        "confidence": 0.95,
        "x": 320.5,
        "y": 240.3,
        "width": 50.0,
        "height": 45.0
      }
    ]
  },
  "humans": {
    "detected": false,
    "count": 0,
    "details": []
  },
  "vehicles": {
    "detected": true,
    "count": 2,
    "details": [
      {"label": "car", "confidence": 0.92},
      {"label": "truck", "confidence": 0.88}
    ]
  },
  "animals": {
    "detected": false,
    "count": 0,
    "details": []
  },
  "velocity_kmh": 45.2
}
```

### Mode Behavior

#### REVERSE Mode (Low Latency)
- **Trigger**: `velocity_kmh < 0` or `mode=reverse`
- **Latency**: <100ms
- **Models Used**: YOLOv8n only
- **Detections**: Humans, Vehicles, Animals
- **Pothole Detection**: SKIPPED
- **Use Case**: Backing up, parking, maneuvering

#### DRIVING Mode (High Accuracy)  
- **Trigger**: `velocity_kmh ≥ 0` or `mode=driving` (default)
- **Latency**: <500ms
- **Models Used**: Roboflow Pothole + YOLOv8n
- **Detections**: All (potholes, humans, vehicles, animals)
- **Pothole Detection**: ENABLED
- **Use Case**: Forward motion, highway driving, normal operation

---

## Performance Metrics

| Metric | Reverse Mode | Driving Mode |
|--------|--------------|--------------|
| Latency | ~80-120ms | ~400-600ms |
| Frame Size | ~65-80 KB (JPEG) | ~65-80 KB |
| Bandwidth | ~65 KB/s @ 1 fps | ~65 KB/s @ 1 fps |
| Models | 1 (YOLOv8n) | 2 (Roboflow + YOLOv8n) |
| Accuracy | Medium (objects) | High (pothole + objects) |

---

## Next Steps

1. **Integrate with Mobile App**: Stream results to Flutter app
2. **Add MQTT**: Replace HTTP POST with MQTT for lower latency
3. **Edge TFLite**: Convert models to TensorFlow Lite for local inference
4. **Cloud Storage**: Upload detections to cloud database
5. **Video Streaming**: Add MJPEG streaming to local dashboard

---

## Support & Issues

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review FastAPI backend logs: `uvicorn app.main:app --log-level debug`
3. Enable debug mode in firmware: `DEBUG = True`
4. Check GitHub Issues: [PotholeNet Repository]

---

## License

MIT License - See LICENSE file

---

**Last Updated**: May 13, 2026  
**Firmware Version**: 1.0.0  
**Backend Version**: 1.0.0
