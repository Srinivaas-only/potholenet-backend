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
8. [Phone Integration](#phone-integration)

---

## Hardware Setup

### Components Needed
- **AI Thinker ESP32-CAM** (with USB port)
- **USB Cable** (micro USB)
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

### Phone GPS Integration

**No hardware GPS module needed!** Speed is provided by the phone app via WiFi:
- Phone app captures GPS location continuously
- Phone calculates vehicle speed from location deltas
- Phone sends speed to backend via `POST /location/update`
- Backend determines REVERSE/DRIVING mode automatically
- ESP32-CAM captures frames only (no GPS hardware)

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

### Step 1: Update Configuration (Optional)

Edit `esp32_cam_firmware.py` to customize Access Point settings:

```python
# Access Point (AP) Configuration
# ESP32-CAM creates its own WiFi network
AP_SSID = "PotholeNet-ESP32"        # WiFi network name (what you see in WiFi list)
AP_PASSWORD = "pothole123"          # WiFi password (8+ characters)

# Backend Server Configuration
BACKEND_HOST = "192.168.4.1"        # ESP32's AP IP (don't change)
BACKEND_PORT = 8000
```

**Customize to your preference:**
```python
AP_SSID = "MyDashcam"               # Change network name
AP_PASSWORD = "MySecurePassword123" # Change password (8+ chars)
```

**Note**: `BACKEND_HOST` must stay as `192.168.4.1` (ESP32's default AP IP)

### Step 2: Upload Firmware

```bash
# Copy firmware to device as main.py (auto-runs on boot)
ampy --port COM3 put esp32_cam_firmware.py main.py
```

### Step 3: Verify Upload

```bash
# List files on device
ampy --port COM3 ls

# Expected output:
# boot.py
# main.py
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

### Access Point (AP) Mode Settings
```python
# ESP32-CAM broadcasts its own WiFi network
AP_SSID = "PotholeNet-ESP32"        # Network name (visible in WiFi list)
AP_PASSWORD = "pothole123"          # WiFi password
AP_IP = "192.168.4.1"               # ESP32's IP (fixed, don't change)
```

### Backend Server
```python
# When using AP mode, connect directly to ESP32's IP
BACKEND_HOST = "192.168.4.1"        # ESP32's AP IP (must match AP_IP)
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
```

### Phone GPS Configuration

**No configuration needed for GPS!** The phone app provides speed:

```python
# Backend automatically receives phone speed via:
# POST /location/update?velocity_kmh=45.5

# Mode detection is automatic:
# - velocity_kmh < 0: REVERSE mode
# - velocity_kmh >= 0: DRIVING mode
```

### Detection Modes
The firmware automatically switches modes:
- **REVERSE**: `velocity_kmh < 0` → YOLO-only (fast, <100ms)
- **DRIVING**: `velocity_kmh ≥ 0` → Full detection (accurate, <500ms)

---

## Testing

### 1. Connect to ESP32's WiFi

Once device starts, it broadcasts a WiFi network:
- **Network Name (SSID)**: `PotholeNet-ESP32`
- **Password**: `pothole123`

**Steps to connect:**

#### Windows/Mac/Linux:
1. Open WiFi settings
2. Look for network: **"PotholeNet-ESP32"**
3. Click "Connect"
4. Enter password: **"pothole123"**
5. Wait for connection

#### Android:
1. Settings → WiFi
2. Scan networks
3. Tap "PotholeNet-ESP32"
4. Enter "pothole123"
5. Connect

#### iPhone:
1. Settings → WiFi
2. Select "PotholeNet-ESP32"
3. Enter "pothole123"
4. Tap Join

### 2. Check Serial Output

```bash
# Monitor ESP32 output using any serial monitor at 115200 baud
# Or use PuTTY, Arduino IDE Serial Monitor, or similar tools
```

**Connect with:**
- **Port**: COM3 (or your device's port)
- **Baud Rate**: 115200
- **Data Bits**: 8
- **Stop Bits**: 1
- **Parity**: None

### 3. Expected Serial Output

```
[INFO] ==================================================
[INFO] PotholeNet ESP32-CAM Dashboard Camera Starting
[INFO] ==================================================
[INFO] Camera initialized successfully
[INFO] Starting Access Point: PotholeNet-ESP32...
[INFO] ✓ Access Point Active!
[INFO]   Network: PotholeNet-ESP32
[INFO]   Password: pothole123
[INFO]   IP: 192.168.4.1
[INFO]   Backend: http://192.168.4.1:8000/detect/dual-mode
[INFO]
[INFO] Connect your device:
[INFO]   1. WiFi SSID: PotholeNet-ESP32
[INFO]   2. Password: pothole123
[INFO]   3. Access API at http://192.168.4.1:8000
[INFO]
[INFO] Ready for detection. Starting capture loop...
[DEBUG] Capturing frame 1...
[INFO] Sending frame 1 (65432 bytes, mode=driving, velocity=45.2 km/h)
[INFO] Alert: ⚠️ POTHOLE DETECTED | 🚗 VEHICLE NEARBY (Mode: DRIVING)
[DEBUG] Free memory: 245632 bytes
```

### 4. Test with curl (from your connected device)

**Important**: First connect your computer/phone to the "PotholeNet-ESP32" WiFi network!

```bash
# Test dual-mode endpoint with image file
# Make sure you're on the PotholeNet-ESP32 WiFi network first!
curl -X POST \
  -F "image=@test_image.jpg" \
  -F "mode=driving" \
  -F "velocity_kmh=50.0" \
  http://192.168.4.1:8000/detect/dual-mode

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

### 5. Test Reverse Mode

```bash
# Simulate reverse (negative velocity)
# Connected to PotholeNet-ESP32 WiFi first!
curl -X POST \
  -F "image=@test_image.jpg" \
  -F "mode=reverse" \
  -F "velocity_kmh=-10.0" \
  http://192.168.4.1:8000/detect/dual-mode

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

### Access Point Won't Start

**Problem**: `[ERROR] AP startup error` or "PotholeNet-ESP32" not appearing in WiFi list

**Solutions**:
1. Verify AP_SSID and AP_PASSWORD in firmware
2. Check antenna is properly connected to ESP32
3. Verify power supply is stable (USB port may need external power)
4. Restart ESP32 (press RST button)
5. Check if AP_PASSWORD is at least 8 characters

```python
# Diagnostic: Test AP mode manually
import network
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='TestNet', password='testpass123')
print(ap.ifconfig())  # Should show 192.168.4.1
```

### Backend Won't Respond

**Problem**: `[ERROR] HTTP POST error` or `[ERROR] Detection failed`

**Solutions**:
1. Verify you're connected to "PotholeNet-ESP32" WiFi
2. Check ESP32 IP: `ping 192.168.4.1` should respond
3. Verify backend is running on ESP32 (check serial output shows "Access Point Active!")
4. Test endpoint: `curl http://192.168.4.1:8000/docs` should work
5. Check firewall allows port 8000
6. Monitor ESP32 serial logs for HTTP errors

### Out of Memory

**Problem**: `[ERROR] Memory allocation failed`

**Solutions**:
1. Reduce `FRAME_INTERVAL` to capture less frequently
2. Use lower image quality:
   ```python
   camera.init(..., quality=20)  # Lower = better quality = more memory
   ```
3. Restart device to clear memory leaks

### Phone GPS Speed Not Updating

**Problem**: Backend always uses default DRIVING mode

**Solutions**:
1. Verify phone app is running and has GPS enabled
2. Check phone has location permission for the app
3. Phone must be connected to PotholeNet-ESP32 WiFi
4. Test phone GPS manually:
   ```bash
   curl -X POST http://192.168.4.1:8000/location/update -F "velocity_kmh=45.5"
   # Should return: {"status":"ok","velocity_kmh":45.5,...}
   ```
5. Check backend logs for speed updates:
   ```bash
   # Run backend with debug logging
   uvicorn app.main:app --log-level debug
   # Look for: "Phone GPS speed updated: X km/h"
   ```

---

## API Documentation

### Dual-Mode Detection Endpoint

**URL**: `POST /detect/dual-mode`

**Parameters**:
| Parameter | Type | Required | Range | Description |
|-----------|------|----------|-------|-------------|
| `image` | File (JPEG/PNG) | ✓ | - | Camera frame image |
| `mode` | String | ✗ | `reverse`, `driving` | Force mode (default: auto-detect from phone GPS) |

**How Mode Detection Works**:
1. Phone sends current speed via `POST /location/update`
2. Backend stores latest speed from phone GPS
3. When ESP32 sends image via `/detect/dual-mode`:
   - If `mode` parameter = "reverse" or "driving": use that
   - If `mode` = None: auto-detect from phone speed
     - velocity_kmh < 0: REVERSE mode
     - velocity_kmh ≥ 0: DRIVING mode

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

### Phone Location Update Endpoint

**URL**: `POST /location/update`

**Purpose**: Phone app sends current GPS speed and location to determine mode and record pothole locations

**Parameters**:
| Parameter | Type | Required | Range | Description |
|-----------|------|----------|-------|-------------|
| `velocity_kmh` | float | ✓ | -150 to 250 | Vehicle velocity in km/h (negative = reverse) |
| `latitude` | float | ✗ | -90 to 90 | Phone GPS latitude |
| `longitude` | float | ✗ | -180 to 180 | Phone GPS longitude |

**Example** (Phone app calls this every GPS update):
```bash
# Phone detects moving at 45.5 km/h forward at location
curl -X POST http://192.168.4.1:8000/location/update \
  -F "velocity_kmh=45.5" \
  -F "latitude=3.1234" \
  -F "longitude=101.5678"

# Phone detects reversing at -10 km/h
curl -X POST http://192.168.4.1:8000/location/update \
  -F "velocity_kmh=-10.0" \
  -F "latitude=3.1234" \
  -F "longitude=101.5678"
```

**Response**:
```json
{
  "status": "ok",
  "velocity_kmh": 45.5,
  "latitude": 3.1234,
  "longitude": 101.5678,
  "timestamp": 1715587200.123
}
```

### Get Current Speed Endpoint

**URL**: `GET /location/current-speed`

**Purpose**: Check the latest phone GPS speed and location stored by backend

**Response**:
```json
{
  "velocity_kmh": 45.5,
  "latitude": 3.1234,
  "longitude": 101.5678,
  "last_update": 1715587200.123
}
```

If phone hasn't sent an update yet:
```json
{
  "velocity_kmh": null,
  "latitude": null,
  "longitude": null,
  "last_update": null
}
```

---

## Phone Integration

### How Phone GPS Works

The system uses the **phone app to provide vehicle speed** for mode detection:

```
┌─────────────────────────────────────────────────────────────┐
│ PHONE APP                                                     │
│ ├─ GPS Location Sensor (every 1-2 seconds)                  │
│ ├─ Calculate Velocity (current location - previous location) │
│ └─ Send POST /location/update with velocity_kmh             │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BACKEND (FastAPI)                                             │
│ ├─ Receive velocity from phone                              │
│ ├─ Store latest velocity in memory                          │
│ └─ ESP32 queries /detect/dual-mode → auto-detect mode      │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ ESP32-CAM                                                     │
│ ├─ Capture JPEG frame                                       │
│ ├─ Send to /detect/dual-mode (no GPS needed)                │
│ └─ Backend uses phone's speed to choose REVERSE or DRIVING  │
└─────────────────────────────────────────────────────────────┘
```

### Phone App Implementation

Your phone app should:

1. **Enable GPS Location** (high accuracy)
2. **Calculate speed** from location changes:
   ```python
   # Pseudocode
   distance = calculate_distance(prev_lat, prev_lng, curr_lat, curr_lng)  # meters
   time_delta = current_time - prev_time  # seconds
   velocity_kmh = (distance / time_delta) * 3.6  # convert m/s to km/h
   ```
3. **Send speed to backend** every 1-2 seconds:
   ```python
   POST /location/update
   velocity_kmh = velocity_kmh (or negative if reversing)
   ```

### Mode Detection Logic

Backend determines mode automatically:

```python
if phone_velocity < 0:
    mode = "REVERSE"  # Fast path: YOLO only, <100ms
else:
    mode = "DRIVING"  # Full path: Pothole + YOLO, <500ms
```

### Requirements for Phone App

- **Location Permission**: Required to get GPS coordinates
- **WiFi Connection**: Must connect to "PotholeNet-ESP32" network
- **HTTP Support**: POST requests to `http://192.168.4.1:8000`
- **Continuous GPS**: Should update speed while driving
- **Background Mode**: Should send updates even if app is minimized

### Testing Phone Integration

```bash
# Test if backend receives phone location updates
curl -X POST http://192.168.4.1:8000/location/update \
  -F "velocity_kmh=45.5"

# Should return:
# {"status":"ok","velocity_kmh":45.5,"timestamp":1715587200.123}

# Check current speed stored by backend
curl http://192.168.4.1:8000/location/current-speed

# Should return:
# {"velocity_kmh":45.5,"last_update":1715587200.123}

# Now send image - backend will use phone's speed to auto-detect mode
curl -X POST http://192.168.4.1:8000/detect/dual-mode \
  -F "image=@test_image.jpg"

# Check response to verify correct mode was selected
```

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

1. **Integrate with Mobile App**: Implement POST /location/update in phone app
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

---

## Pothole Detection Recording

### Automatic Recording

Every time a pothole is detected, the backend automatically saves it with location, time, and confidence to the database.

### What Gets Recorded

When a pothole is detected:
- **Location**: Latitude/Longitude (from phone GPS at detection time)
- **Time**: Exact timestamp of detection
- **Date**: Included in ISO 8601 timestamp format
- **Confidence**: Detection confidence score (0-1)
- **Speed**: Vehicle velocity at detection
- **Mode**: REVERSE or DRIVING
- **Count**: Number of potholes detected in frame

### Database Storage

Potholes are automatically saved to SQLite database table `pothole_detections` with these fields:

- `id`: Unique detection ID
- `latitude`: Phone GPS latitude at detection
- `longitude`: Phone GPS longitude at detection
- `confidence`: Detection confidence (0-1)
- `velocity_kmh`: Vehicle speed
- `mode`: REVERSE or DRIVING
- `detected_at`: Timestamp of detection (ISO 8601)
- `pothole_count`: Number of potholes in frame

### Accessing Recorded Potholes

Query the database directly:

\\\ash
# Query recent detections
sqlite3 potholenet.db \SELECT latitude, longitude, confidence, detected_at FROM pothole_detections ORDER BY detected_at DESC LIMIT 10;\`n
# Find potholes in a region (latitude 3.1-3.2, longitude 101.5-101.6)
sqlite3 potholenet.db \SELECT id, latitude, longitude, confidence FROM pothole_detections WHERE latitude BETWEEN 3.1 AND 3.2 AND longitude BETWEEN 101.5 AND 101.6;\`n
# Count potholes by day
sqlite3 potholenet.db \SELECT DATE(detected_at), COUNT(*) FROM pothole_detections GROUP BY DATE(detected_at);\`n\\\`n
### Requirements for Recording

For full pothole recording with location:
1. Phone sends GPS coordinates via `POST /location/update` (latitude, longitude, velocity)
2. Pothole detected in DRIVING mode (Roboflow model active)
3. Backend has SQLite database (auto-created on startup)

If phone doesn't send coordinates, location will be NULL but detection is still recorded.
