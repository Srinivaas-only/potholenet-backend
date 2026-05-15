# Arduino IDE: ESP32 Upload Guide from Scratch

Complete step-by-step guide to upload PotholeNet firmware to AI Thinker ESP32-CAM using Arduino IDE.

## Table of Contents
1. [Check Your ESP32 Type](#check-your-esp32-type)
2. [Hardware Setup](#hardware-setup)
3. [Install Arduino IDE](#install-arduino-ide)
4. [Install ESP32 Board Support](#install-esp32-board-support)
5. [Connect ESP32 to Computer](#connect-esp32-to-computer)
6. [Upload Firmware](#upload-firmware)
7. [Troubleshooting](#troubleshooting)

---

## Check Your ESP32 Type

### Does Your ESP32-CAM Have a Built-in USB Port?

**YES - Built-in USB Port** (USB-C or Micro-B on the board) ✅
- **Skip the converter entirely** - connect directly to your computer
- Jump to [Connect ESP32 to Computer](#connect-esp32-to-computer)
- Much simpler!

**NO - No USB Port** (only 6 header pins)
- You need a USB-to-Serial converter
- Follow [Hardware Setup](#hardware-setup) below

---

## Hardware Setup

### What You Need (If NO Built-in USB)

- **AI Thinker ESP32-CAM** development board (without USB port)
- **USB-to-Serial Converter** (FTDI FT232RL or CH340 recommended)
- **USB Cable** (Type-A to Micro-B)
- **Jumper Wires** (Male-to-Female)
- **3.3V Power Supply** (or USB power from converter)

### Wiring Diagram: USB-to-Serial Converter to ESP32-CAM

**ONLY IF YOU DON'T HAVE BUILT-IN USB ON YOUR BOARD**

```
USB Converter          ESP32-CAM
─────────────────────────────────
GND (Black)    ──────  GND (Pin 19)
VCC (Red)      ──────  3.3V / 5V (Pin 18)
TX (Yellow)    ──────  U0R (Pin 1)
RX (Green)     ──────  U0T (Pin 3)

Additional Connections for Upload Mode:
───────────────────────────────────────
GPIO 0 (Pin 12) ──────  GND (Put HIGH after upload to run)
IO13/IO12       ──────  Optional: Debug LEDs
```

### Connection Notes

| Signal | Arduino Name | ESP32-CAM Pin | Description |
|--------|--------------|---------------|-------------|
| GND | Ground | Pin 19 (GND) | Common ground (CRITICAL) |
| 3.3V | Power | Pin 18 (3.3V) | Power supply |
| TX | Data to ESP32 | Pin 1 (U0R) | Serial transmit |
| RX | Data from ESP32 | Pin 3 (U0T) | Serial receive |
| GPIO 0 | Boot Mode | Pin 12 | **MUST be GND for upload** |

### Upload Mode vs Run Mode

**Upload Mode (Flash Code)**:
- GPIO 0 → GND (pulled LOW)
- Power on board
- Arduino IDE detects device
- Upload proceeds

**Run Mode (Normal Operation)**:
- GPIO 0 → VCC or floating (pulled HIGH)
- Power on board
- Firmware executes

---

## Install Arduino IDE

### Step 1: Download Arduino IDE

1. Visit [arduino.cc/en/software](https://www.arduino.cc/en/software)
2. Download **Arduino IDE 2.x** (Latest version recommended)
   - Windows: `Arduino IDE 2.x Setup.exe`
   - Mac: `Arduino IDE 2.x.dmg`
   - Linux: Tar or AppImage

### Step 2: Install Arduino IDE

**Windows**:
- Double-click `Arduino IDE Setup.exe`
- Follow installation wizard
- Choose installation directory (default: `C:\Program Files\Arduino IDE`)
- Click "Install"
- Wait for completion (~5 minutes)

**Mac**:
- Double-click `Arduino IDE 2.x.dmg`
- Drag Arduino IDE to Applications folder
- Open Applications → Arduino IDE

**Linux**:
```bash
# Extract and run
tar xzf arduino-ide_*.tar.gz
cd arduino-ide_*
./arduino-ide
```

### Step 3: Launch Arduino IDE

- Windows: Click Windows Start menu → Search "Arduino IDE"
- Mac: Applications → Arduino IDE
- Linux: Run `./arduino-ide` from extracted folder

You should see the Arduino IDE editor with an empty sketch.

---

## Install ESP32 Board Support

### Step 1: Add ESP32 Board URL

1. Open Arduino IDE
2. Click **File** → **Preferences** (Windows/Linux) or **Arduino IDE** → **Preferences** (Mac)
3. Find "Additional boards manager URLs" field
4. Paste this URL:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
5. Click **OK**

### Step 2: Install ESP32 Board Package

1. Click **Tools** → **Board** → **Boards Manager**
2. Search for "ESP32" in the search box
3. You should see "esp32 by Espressif Systems"
4. Click it and select latest version
5. Click **Install** (takes 2-3 minutes)
6. Wait until you see "INSTALLED" label
7. Close Boards Manager

### Step 3: Verify Installation

1. Click **Tools** → **Board**
2. You should see "ESP32 boards" section with options like:
   - AI Thinker ESP32-CAM
   - ESP32-WROOM-32
   - ESP32-S3

If you see these, installation is successful!

---

## Connect ESP32 to Computer

### If Your ESP32-CAM HAS Built-in USB Port ⭐ (EASIEST)

1. **Take the USB Cable** (USB-C or Micro-B depending on your board)
2. **Plug one end into the ESP32's USB port**
3. **Plug the other end into your computer USB port**
4. **Wait 2 seconds** for driver initialization
5. **Done!** Arduino IDE will auto-detect the port

**No GPIO 0 connections needed, no jumper wires needed, no converter needed!**

### If Your ESP32-CAM DOESN'T Have Built-in USB (Converter Method)

If you only have header pins (no USB port on board):

#### Step 1: Wire the USB-to-Serial Converter

```
USB Converter Pins          ESP32-CAM Pins
──────────────────────────────────────────
GND (Black)      →   GND (Pin 19)
3.3V (Red)       →   3.3V (Pin 18)
TX (Yellow)      →   U0R (Pin 1)
RX (Green)       →   U0T (Pin 3)
#### Step 1: Wire the USB-to-Serial Converter

Connect your USB converter to the ESP32-CAM **before** connecting to your PC:

```
USB Converter Pins          ESP32-CAM Pins
──────────────────────────────────────────
GND (Black)      →   GND (Pin 19)
3.3V (Red)       →   3.3V (Pin 18)
TX (Yellow)      →   U0R (Pin 1)
RX (Green)       →   U0T (Pin 3)
```

**CRITICAL for upload**:
- Connect **GPIO 0 (Pin 12) to GND (Pin 19)** to enter upload mode

#### Step 2: Connect USB to Computer

1. Plug the USB cable from the converter into your computer
2. You should see a **LED light up** on the converter (usually red)
3. Wait 2 seconds for driver initialization

#### Step 3: Check Device Manager (Windows)

1. Right-click **Start** menu
2. Click **Device Manager**
3. Expand **Ports (COM & LPT)**
4. You should see a new port:
   - **CH340 chip**: "USB-SERIAL CH340"
   - **FTDI chip**: "USB Serial Port (COMx)"
5. Note the **COM port number** (e.g., COM3, COM5)

**If you don't see the port**:
- Check USB cable connection
- Try a different USB port on your computer
- See [Troubleshooting](#troubleshooting) section

---

### Check Device Manager (Windows) - For Built-in USB

1. Right-click **Start** menu
2. Click **Device Manager**
3. Expand **Ports (COM & LPT)**
4. You should see your ESP32:
   - **USB-SERIAL CH340** or similar
5. Note the **COM port number** (e.g., COM3, COM5)

---

## Upload Firmware

### Step 1: Create/Prepare Your Code

Create a new Arduino sketch (`.ino` file). Here's a minimal example for testing:

```cpp
// Minimal ESP32-CAM Test Sketch
#include <WiFi.h>

const char* ssid = "PotholeNet-ESP32";
const char* password = "pothole123";

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\n\nESP32-CAM Starting...");
  
  // Initialize WiFi in AP mode
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  
  IPAddress IP = WiFi.softAPIP();
  Serial.print("AP IP address: ");
  Serial.println(IP);
}

void loop() {
  delay(1000);
  Serial.println("ESP32 is running!");
}
```

**Or use the full PotholeNet firmware**: Adapt `esp32_cam_firmware.py` (MicroPython) to Arduino C++

### Step 2: Configure Board Settings

1. Click **Tools** → **Board** → **esp32**
2. Select **AI Thinker ESP32-CAM**

3. Click **Tools** → Configure these settings:

| Setting | Value |
|---------|-------|
| **Board** | AI Thinker ESP32-CAM |
| **Upload Speed** | 921600 |
| **CPU Frequency** | 240 MHz |
| **Flash Frequency** | 80 MHz |
| **Flash Mode** | DIO |
| **Flash Size** | 4MB |
| **Partition Scheme** | Huge APP (3MB No OTA) |
| **Core Debug Level** | Verbose |
| **PSRAM** | Enabled |
| **Port** | COM3 (or your detected port) |

### Step 3: Verify Code

1. Click the **✓ (Verify)** button in the top toolbar
2. Wait for compilation (30-60 seconds)
3. You should see "Compilation complete" message

If there are errors, check:
- Missing `#include` statements
- Syntax errors (semicolons, brackets)
- Library availability (see [Troubleshooting](#troubleshooting))

### Step 4: Upload to ESP32

**Pre-upload Checklist**:
- ✅ USB connected to your computer
- ✅ Port detected (Device Manager or Arduino IDE)
- ✅ Port is selected correctly in Tools → Port

**IMPORTANT: If using converter with header pins ONLY**:
- ✅ GPIO 0 is connected to GND (upload mode)

**If ESP32 has BUILT-IN USB**:
- ⏭️ **Skip GPIO 0 connection** - built-in USB handles boot mode automatically

**Upload Steps**:

1. Click the **→ (Upload)** button in top toolbar
2. You should see messages like:
   ```
   Connecting...................._____.....______
   ```
3. Wait for "Writing at" messages (firmware uploading)
4. You should see 100% progress:
   ```
   Wrote 123456 bytes to address 0x00000000 in 5.23 seconds
   ```
5. Upload complete! ✅

### Step 5: Run Firmware

**If ESP32 has BUILT-IN USB**:
1. Just press the **RST (Reset) button** on ESP32 or power cycle
2. Firmware runs automatically

**If using converter with header pins**:
1. **Disconnect GPIO 0 from GND** (remove jumper or wire)
2. **Leave USB converter connected** for power
3. Press the **RST (Reset) button** on ESP32 or power cycle
4. Firmware runs automatically

---

## Serial Monitor

### View ESP32 Output

1. Click **Tools** → **Serial Monitor** (or keyboard shortcut)
2. Set baud rate to **115200** (bottom right corner)
3. You should see output from your sketch:
   ```
   ESP32-CAM Starting...
   AP IP address: 192.168.4.1
   ESP32 is running!
   ESP32 is running!
   ...
   ```

### Send Commands (Optional)

1. Type in the input box at top of Serial Monitor
2. Click **Send** or press Enter
3. Data sent to ESP32's `Serial.read()` function

---

## Troubleshooting

### Issue: Port Not Detected

**Symptoms**: Device Manager shows no COM port

**Solutions**:
1. **Install USB Driver**:
   - CH340: Download from [wch.cn](http://wch.cn/downloads)
   - FTDI: Download from [ftdichip.com](https://ftdichip.com/drivers/)
   - Install and restart computer

2. **Check Physical Connection**:
   - Verify all wires are firmly connected
   - Check for loose pins
   - Try different USB cable (some cables are power-only)

3. **Try Different USB Port**:
   - USB 2.0 ports work better than USB 3.0
   - Try rear ports if using laptop

### Issue: "Failed to connect to ESP32"

**Symptoms**: Upload shows "Connecting..." and hangs

**Solutions**:
1. **Verify GPIO 0 is LOW** (connected to GND)
   - Remove jumper if present
   - Wire GPIO 0 to GND with jumper wire
   - Try upload again

2. **Press Boot Button During Connect**:
   - When you see "Connecting..." messages
   - Press and hold the **BOOT** button on ESP32
   - Hold for 2-3 seconds
   - Release and try upload

3. **Change Upload Speed**:
   - Tools → Upload Speed → **115200**
   - Try slower speed first, then increase

4. **Power Cycle**:
   - Disconnect USB
   - Disconnect GPIO 0 from GND
   - Reconnect USB
   - Reconnect GPIO 0 to GND
   - Try upload

### Issue: "Compilation Error"

**Symptoms**: Red error messages during Verify

**Solutions**:
1. **Check Missing Includes**:
   ```cpp
   #include <WiFi.h>          // Built-in
   #include <WebServer.h>     // Built-in
   #include <esp_camera.h>    // Built-in (ESP32-CAM)
   ```

2. **Verify Board Selected**:
   - Tools → Board → AI Thinker ESP32-CAM (not generic ESP32)

3. **Check Library Versions**:
   - Some libraries have breaking changes
   - Downgrade if issues persist

### Issue: Bootloop (Resets Repeatedly)

**Symptoms**: Serial Monitor shows repeated startup messages

**Solutions**:
1. **Power Issue**: Use separate 3.3V power supply instead of USB converter
2. **Flash Corruption**: Erase entire flash:
   ```
   Tools → Erase All Flash Before Sketch Upload → Enabled
   ```
   Then upload again

3. **Incompatible Code**: Try minimal "blink" sketch to verify hardware works

### Issue: Cannot See Serial Output

**Symptoms**: Serial Monitor is blank

**Solutions**:
1. **Check Baud Rate**: Must be **115200**
2. **Check Port**: Should match Tools → Port
3. **Reset Board**: Press RST button on ESP32
4. **Check RX/TX Wires**: May be reversed (swap them)
5. **Use Verbose Output**: Tools → Core Debug Level → Verbose

---

## PotholeNet-Specific Setup

### Adapting MicroPython Code to Arduino C++

The current firmware is **MicroPython** (`.py`). To use Arduino IDE, you need **C++** (`.ino`).

#### Option 1: Use MicroPython (Recommended if familiar)

1. Flash MicroPython firmware using `esptool.py`:
   ```bash
   pip install esptool
   esptool.py --chip esp32 --port COM3 write_flash -z 0x1000 esp32-20240101-idf4.4-v1.22.1.bin
   ```
2. Use MicroPython IDE (Thonny) to upload Python code
3. Faster development, easier for this project

#### Option 2: Convert to Arduino C++ (More Control)

Create `esp32_cam_dashcam.ino`:

```cpp
#include <WiFi.h>
#include <WebServer.h>
#include <esp_camera.h>

const char* ssid = "PotholeNet-ESP32";
const char* password = "pothole123";

WebServer server(8000);

// Camera pin configuration for AI Thinker ESP32-CAM
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

void setup() {
  Serial.begin(115200);
  delay(2000);
  
  Serial.println("\nPotholeNet ESP32-CAM Starting...");
  
  // Initialize camera
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_VGA;
  config.jpeg_quality = 10;
  config.fb_count = 1;
  
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    return;
  }
  
  // Initialize WiFi AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ssid, password);
  IPAddress IP = WiFi.softAPIP();
  
  Serial.print("AP SSID: ");
  Serial.println(ssid);
  Serial.print("AP IP address: ");
  Serial.println(IP);
  
  // Setup HTTP endpoints
  server.on("/", HTTP_GET, handleRoot);
  server.on("/capture", HTTP_GET, handleCapture);
  server.begin();
  
  Serial.println("Web server started!");
}

void loop() {
  server.handleClient();
  delay(10);
}

void handleRoot() {
  server.send(200, "text/plain", "PotholeNet ESP32-CAM Running!");
}

void handleCapture() {
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  
  if (!fb) {
    server.send(500, "text/plain", "Camera capture failed");
    return;
  }
  
  server.sendHeader("Content-Type", "image/jpeg");
  server.send(200, "image/jpeg", (const char *)fb->buf, fb->len);
  esp_camera_fb_return(fb);
}
```

### Compile and Upload

1. Copy the code above into Arduino IDE
2. Tools → Board → AI Thinker ESP32-CAM
3. Tools → Port → COM3 (your port)
4. Click Upload
5. Test with: `http://192.168.4.1:8000/capture`

---

## Next Steps

### After Successful Upload

1. **Verify WiFi AP**: 
   - Look for "PotholeNet-ESP32" network on your phone
   - Connect to it (password: "pothole123")

2. **Test Camera Endpoint**:
   ```bash
   curl http://192.168.4.1:8000/capture -o test.jpg
   ```

3. **Run Backend Server**:
   ```bash
   python app/main.py
   ```

4. **Send Frames to Backend**:
   ```bash
   # Repeatedly capture and send to backend
   for i in {1..10}; do
     curl -X POST http://192.168.4.1:8000/detect/dual-mode \
       -F "image=@test.jpg" \
       -F "mode=driving"
     sleep 1
   done
   ```

### Debugging Tips

- **Use Serial Monitor** to view print statements
- **Add debug output**: `Serial.printf("Debug: %d\n", variable);`
- **Monitor memory**: `Serial.printf("Free heap: %d\n", ESP.getFreeHeap());`
- **Check WiFi**: Scan for AP using phone's WiFi settings

---

## Additional Resources

| Resource | Link | Purpose |
|----------|------|---------|
| Arduino IDE Docs | [arduino.cc/docs](https://docs.arduino.cc/) | Complete Arduino reference |
| ESP32 Pinout | [pinout.xyz](https://pinout.xyz/pinout/esp32_devkit_v1) | Visual pin reference |
| ESP32 Documentation | [docs.espressif.com](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/hw-reference/esp32_devkitc.html) | Technical specs |
| Espressif Arduino Core | [github.com/espressif/arduino-esp32](https://github.com/espressif/arduino-esp32) | Source code & examples |
| CH340 Driver | [wch.cn/downloads](http://wch.cn/downloads) | USB Serial Driver |
**If your ESP32 has BUILT-IN USB** ⭐ (Easiest):
- [ ] Arduino IDE 2.x installed
- [ ] ESP32 board package installed
- [ ] USB cable plugged in
- [ ] COM port detected in Device Manager
- [ ] Board: "AI Thinker ESP32-CAM" selected
- [ ] Port: Correct COM port selected
- [ ] Code compiled successfully
- [ ] Firmware uploaded successfully
- [ ] Serial Monitor shows output
- [ ] WiFi AP "PotholeNet-ESP32" visible

**If your ESP32 uses CONVERTER with header pins**:
- [ ] Arduino IDE 2.x installed
- [ ] ESP32 board package installed
- [ ] USB-to-Serial converter wired correctly
- [ ] GPIO 0 connected to GND for upload
- [ ] COM port detected in Device Manager
- [ ] Board: "AI Thinker ESP32-CAM" selected
- [ ] Port: Correct COM port selected
- [ ] Code compiled successfully
- [ ] Firmware uploaded successfully
- [ ] GPIO 0 disconnected from GND (run mode)load
- [ ] COM port detected in Device Manager
- [ ] Board: "AI Thinker ESP32-CAM" selected
- [ ] Port: Correct COM port selected
- [ ] Code compiled successfully
- [ ] Firmware uploaded successfully
- [ ] Serial Monitor shows output
- [ ] WiFi AP "PotholeNet-ESP32" visible

Once all checkboxes are done, your ESP32-CAM is ready for PotholeNet dashcam operation! 🎉
