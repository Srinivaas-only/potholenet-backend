# PotholeNet — Hardware Setup Guide

> How to get the ESP32-CAM running and connected to the PotholeNet app on your phone.

---

## What you need

- **AI-Thinker ESP32-CAM** (with built-in USB-C port — your version)
- **USB cable** (Type-A to Type-C, or whatever matches your laptop)
- **A laptop** with the Arduino IDE installed
- **A phone** with a modern browser (Chrome, Safari, Edge — Firefox works too)
- **A 5V power source for production** (USB power bank for the demo, car USB port or buck converter for actual install)

---

## Step 1: Install Arduino IDE + ESP32 board support

1. Download Arduino IDE from https://www.arduino.cc/en/software
2. Open Arduino IDE → **File → Preferences**
3. In "Additional Board Manager URLs" paste:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Open **Tools → Board → Boards Manager**, search for "esp32", install **"esp32 by Espressif Systems"** (version 2.0.14 or later)
5. Open **Tools → Board → ESP32 Arduino → "AI Thinker ESP32-CAM"**

---

## Step 2: Configure upload settings

In **Tools** menu, set:

| Setting | Value |
|---------|-------|
| Board | AI Thinker ESP32-CAM |
| Upload Speed | 115200 |
| Flash Frequency | 80MHz |
| Flash Mode | QIO |
| Partition Scheme | Huge APP (3MB No OTA / 1MB SPIFFS) |
| Core Debug Level | None |
| Port | (whatever COM port your ESP32 appears on) |

---

## Step 3: Flash the firmware

1. Open `PotholeNet_ESP32_Firmware.ino` in Arduino IDE
2. Plug in the ESP32-CAM via USB
3. Check the COM port (Tools → Port)
4. Click the **Upload** button (right-arrow icon)
5. Wait — it takes 30-60 seconds

**If upload fails with "Failed to connect" or "Timed out waiting for packet header":**
- Press and hold the **RST** button on the ESP32-CAM
- Click Upload in Arduino IDE
- When you see "Connecting…" in the console, release the RST button
- If the board has a GPIO0 jumper or pin, connect GPIO0 to GND before powering on, upload, then remove the jumper and reset

**Your USB-C board with built-in USB should auto-reset.** Older boards without USB need an FTDI adapter.

---

## Step 4: Verify it's working

1. After upload completes, open **Tools → Serial Monitor** (set baud rate to 115200)
2. Press the RST button on the board
3. You should see:
   ```
   ======================================
     PotholeNet ESP32-CAM Started
   ======================================
     SSID:     PotholeNet-AP
     Password: potholenet
     IP:       192.168.4.1
     Stream:   http://192.168.4.1:81/stream
     Control:  http://192.168.4.1/control
   ======================================
   ```
4. The flash LED on the board will blink 3 times to confirm ready, then once every 3 seconds as a heartbeat

---

## Step 5: Connect from your phone

1. On your phone, open Wi-Fi settings
2. Look for the network **`PotholeNet-AP`**
3. Tap it, password is `potholenet`
4. Your phone will say "no internet" — that's correct. The ESP32 is not connected to anything upstream.
5. **Important on Android:** A popup may ask "Stay connected to this network?" — tap **Yes**. Android sometimes auto-disconnects from networks without internet.
6. **Important on iOS:** Same thing — confirm "Use without internet" if prompted

---

## Step 6: Test the stream in the phone browser

Before opening the PotholeNet app, verify the stream works directly:

1. Open Chrome/Safari on the phone
2. Go to `http://192.168.4.1`
3. You should see the PotholeNet status page
4. Tap the stream link, or go directly to `http://192.168.4.1:81/stream`
5. You should see live video from the ESP32-CAM

**If you see the status page but no video:**
- The camera may have failed to initialize. Check the Serial Monitor for errors.
- Try a power cycle.
- The OV2640 module might be loose — check the ribbon cable connector on the board.

**If you can't reach 192.168.4.1 at all:**
- Confirm phone is connected to PotholeNet-AP
- Some Android versions disable network access when there's no internet — go to Wi-Fi advanced settings and disable "Auto-switch to mobile data" for this network.

---

## Step 7: Open the PotholeNet app

Once the stream works, open the PotholeNet web app URL on your phone. The app will:

1. Detect the ESP32-CAM by pinging `http://192.168.4.1/heartbeat`
2. If reachable, load the live MJPEG stream
3. Start running TensorFlow.js detection on the stream
4. Show alerts when objects are detected

If the heartbeat fails 3 times in a row, the app falls back to DEMO mode automatically.

---

## Common issues & fixes

### Issue: Stream is laggy (>1 second delay)
- Lower the resolution in firmware: change `FRAMESIZE_VGA` to `FRAMESIZE_QVGA`
- Lower JPEG quality: change `config.jpeg_quality = 10` to `config.jpeg_quality = 15` (higher number = lower quality, less data)
- Make sure no other devices are connected to the AP

### Issue: ESP32-CAM keeps rebooting
- Power supply is insufficient. The ESP32-CAM needs at least 5V @ 500mA during streaming. Use a quality USB cable and a 2A+ power source.
- A power bank with auto-shutoff may turn off if the ESP32 draws too little during idle. Use a power bank without auto-shutoff or one designed for low-draw devices.

### Issue: Brown image or color is off
- White balance is wrong. In firmware, add after sensor init:
  ```cpp
  s->set_whitebal(s, 1);      // enable white balance
  s->set_awb_gain(s, 1);      // enable auto white balance gain
  s->set_wb_mode(s, 0);       // 0 = auto
  ```

### Issue: Image is upside-down
- The firmware already calls `set_vflip(s, 1)` and `set_hmirror(s, 1)` for rear-camera mounting. If your physical mounting is different, toggle these.

### Issue: Phone won't stay connected to PotholeNet-AP
- This is the most common issue. Mobile OSes don't like networks without internet.
- **Android fix:** Wi-Fi → long-press PotholeNet-AP → Modify → Advanced → set "No Internet" to "Always Connect"
- **iOS fix:** Settings → Wi-Fi → tap (i) next to PotholeNet-AP → enable "Auto-Join"; if it disconnects anyway, toggle Cellular Data off temporarily during the demo

### Issue: Multiple devices can't connect
- The firmware caps at 4 clients via `MAX_CLIENTS`. Increase if needed, but ESP32 AP performance degrades with >2 active streamers.

---

## Production install (post-hackathon)

For a real install in a car:

1. Tap into the reverse light wire (12V) at the rear light cluster
2. Use a 12V-to-5V buck converter (LM2596 or similar)
3. Wire the buck converter's 5V output to the ESP32-CAM's 5V pin (or USB)
4. The camera powers on only when the car is in reverse
5. Mount the camera in a weatherproof enclosure pointed rearward
6. The phone stays connected via the same Wi-Fi AP

For the hackathon demo, just use a USB power bank — far simpler.

---

## Network details for the app developer

| Endpoint | Method | Purpose | Response |
|----------|--------|---------|----------|
| `http://192.168.4.1/` | GET | Status page | HTML |
| `http://192.168.4.1/heartbeat` | GET | Liveness check | `{"alive":true,"uptime":N,"clients":N}` |
| `http://192.168.4.1/control?led=on` | GET | Turn on flash LED | `{"status":"ok"}` |
| `http://192.168.4.1/control?led=off` | GET | Turn off flash LED | `{"status":"ok"}` |
| `http://192.168.4.1:81/stream` | GET | MJPEG video stream | `multipart/x-mixed-replace` |

All endpoints set `Access-Control-Allow-Origin: *` so the web app can call them from any origin.

**Stream behavior:**
- Format: MJPEG (multipart JPEG)
- Resolution: VGA (640x480) by default
- Frame rate: ~15-20 FPS
- Latency: ~150-200ms glass-to-glass

**To use the stream in HTML:**
```html
<img src="http://192.168.4.1:81/stream" />
```
That's it. The browser handles MJPEG natively as an animated image.

---

## Hardware specs reference

| Component | Detail |
|-----------|--------|
| Chip | ESP32-S (240MHz dual-core, Wi-Fi b/g/n, BLE) |
| Camera | OV2640, 2MP, JPEG/YUV output |
| Wi-Fi | 2.4GHz only, AP mode supports up to 4 clients |
| RAM | 520KB SRAM + 4MB PSRAM (PSRAM required for higher resolutions) |
| Flash | 4MB |
| Power | 5V via USB or 5V pin, ~250mA idle, ~500mA streaming |
| GPIO | Limited (most pins used by camera/SD); GPIO 4 = flash LED, GPIO 12-15 reserved |
