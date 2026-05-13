"""
PotholeNet ESP32-CAM Firmware (MicroPython)
Real-time dual-mode pothole detection for vehicle dashcam
Upload to ESP32-CAM using: ampy --port COM3 put esp32_cam_firmware.py main.py
"""

import camera
import esp
import gc
import json
import machine
import micropython
import network
import socket
import sys
import time
from machine import UART, Pin

# ============================================================================
# CONFIGURATION (Update these for your setup)
# ============================================================================

# WiFi Configuration
WIFI_SSID = "YOUR_SSID"
WIFI_PASSWORD = "YOUR_PASSWORD"

# Backend Server Configuration
BACKEND_HOST = "192.168.1.100"  # Change to your server IP
BACKEND_PORT = 8000
BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}/detect/dual-mode"

# Camera Configuration
CAMERA_FREQ = 20000000  # 20 MHz
CAMERA_PINS = {
    'pwdn': 32,     # Power down
    'reset': -1,    # Reset (-1 = not used)
    'xclk': 0,      # XCLK
    'siod': 26,     # SIOD (SDA)
    'sioc': 27,     # SIOC (SCL)
    'd0': 5,
    'd1': 18,
    'd2': 19,
    'd3': 21,
    'd4': 36,
    'd5': 39,
    'd6': 34,
    'd7': 35,
    'hsync': 23,
    'vsync': 22,
    'pclk': 25,
}

# GPS Configuration (UART 2)
GPS_UART_NUM = 2
GPS_BAUD = 9600
GPS_RX = 16  # GPIO 16 (RX2)
GPS_TX = 17  # GPIO 17 (TX2)

# Detection Settings
FRAME_INTERVAL = 1.0  # Seconds between frames (1 frame/sec)
LOCATION_INTERVAL = 5.0  # Seconds between GPS updates
LOW_LATENCY_MODE = True  # Enable reverse mode optimization

# Status LED
STATUS_LED_PIN = 4  # GPIO 4 (often used for status on ESP32-CAM)
DEBUG = True

# ============================================================================
# LOGGER & UTILITIES
# ============================================================================

def log(level, msg):
    """Simple logging function"""
    timestamp = time.time()
    if DEBUG or level == "ERROR":
        print(f"[{level}] {msg}")

def log_free_mem():
    """Log available memory"""
    gc.collect()
    mem = gc.mem_free()
    log("DEBUG", f"Free memory: {mem} bytes")

# ============================================================================
# LED CONTROL
# ============================================================================

class StatusLED:
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
    
    def on(self):
        self.pin.on()
    
    def off(self):
        self.pin.off()
    
    def blink(self, count=1, interval=0.2):
        """Blink LED count times"""
        for _ in range(count):
            self.on()
            time.sleep(interval)
            self.off()
            time.sleep(interval)
    
    def pulse(self):
        """Pulse effect"""
        self.on()
        time.sleep(0.1)
        self.off()

led = StatusLED(STATUS_LED_PIN)

# ============================================================================
# GPS PARSER
# ============================================================================

class GPSParser:
    """Parse NMEA GPS data from serial UART"""
    
    def __init__(self, uart_num=2, rx_pin=16, tx_pin=17, baud=9600):
        self.uart = UART(uart_num, baud, rx=rx_pin, tx=tx_pin, timeout=100)
        self.latitude = 0.0
        self.longitude = 0.0
        self.velocity_kmh = 0.0
        self.satellites = 0
        self.fix_type = 0
    
    def read_sentence(self):
        """Read and parse NMEA sentence"""
        try:
            if self.uart.any():
                line = self.uart.readline()
                if line:
                    self._parse_nmea(line.decode('utf-8', errors='ignore').strip())
        except Exception as e:
            log("ERROR", f"GPS read error: {e}")
    
    def _parse_nmea(self, sentence):
        """Parse NMEA sentence"""
        try:
            if sentence.startswith('$GPRMC'):
                # RMC: Recommended Minimum Navigation Info
                parts = sentence.split(',')
                if len(parts) > 7 and parts[2] == 'A':  # A = Active
                    # Parse latitude
                    if len(parts) > 3:
                        lat_str = parts[3]
                        if lat_str:
                            self.latitude = self._dms_to_decimal(lat_str)
                    # Parse longitude
                    if len(parts) > 5:
                        lon_str = parts[5]
                        if lon_str:
                            self.longitude = self._dms_to_decimal(lon_str)
                    # Parse velocity (knots to km/h)
                    if len(parts) > 7:
                        try:
                            velocity_knots = float(parts[7])
                            self.velocity_kmh = velocity_knots * 1.852
                        except:
                            pass
            
            elif sentence.startswith('$GPGGA'):
                # GGA: Fix and satellites
                parts = sentence.split(',')
                if len(parts) > 7:
                    try:
                        self.satellites = int(parts[7])
                        self.fix_type = int(parts[6])
                    except:
                        pass
        except Exception as e:
            log("DEBUG", f"NMEA parse error: {e}")
    
    @staticmethod
    def _dms_to_decimal(dms_str):
        """Convert DMS string to decimal degrees"""
        try:
            degrees = float(dms_str[:2])
            minutes = float(dms_str[2:])
            decimal = degrees + (minutes / 60.0)
            return decimal
        except:
            return 0.0
    
    def get_status(self):
        """Return GPS status dict"""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'velocity_kmh': self.velocity_kmh,
            'satellites': self.satellites,
            'fix_type': self.fix_type,
        }

# ============================================================================
# CAMERA CONTROL
# ============================================================================

class CameraController:
    def __init__(self):
        self.initialized = False
    
    def init_camera(self):
        """Initialize OV2640 camera"""
        try:
            camera.init(
                0,  # Camera module (ESP32-CAM has only one)
                format=camera.JPEG,
                framesize=camera.FRAME_VGA,  # 640x480
                quality=10,  # 1-63, lower=better quality
                flip=False,
                mirror=True,
            )
            
            # Additional settings
            camera.saturation(0)   # -2 to 2
            camera.brightness(0)   # -2 to 2
            camera.contrast(0)     # -2 to 2
            camera.hmirror(False)
            camera.vflip(False)
            
            self.initialized = True
            log("INFO", "Camera initialized successfully")
            led.blink(2)
            return True
        except Exception as e:
            log("ERROR", f"Camera init failed: {e}")
            led.blink(5)
            return False
    
    def capture_jpeg(self):
        """Capture JPEG frame"""
        try:
            buf = camera.capture()
            return bytes(buf) if buf else None
        except Exception as e:
            log("ERROR", f"Capture failed: {e}")
            return None

camera_ctrl = CameraController()

# ============================================================================
# WIFI CONNECTIVITY
# ============================================================================

class WiFiManager:
    def __init__(self, ssid, password):
        self.ssid = ssid
        self.password = password
        self.wlan = network.WLAN(network.STA_IF)
    
    def connect(self, timeout=10):
        """Connect to WiFi"""
        try:
            self.wlan.active(True)
            if not self.wlan.isconnected():
                log("INFO", f"Connecting to {self.ssid}...")
                self.wlan.connect(self.ssid, self.password)
                
                start = time.time()
                while not self.wlan.isconnected() and (time.time() - start) < timeout:
                    led.pulse()
                    time.sleep(0.5)
                
                if self.wlan.isconnected():
                    ip_info = self.wlan.ifconfig()
                    log("INFO", f"Connected! IP: {ip_info[0]}")
                    led.on()
                    return True
                else:
                    log("ERROR", "WiFi connection timeout")
                    led.off()
                    return False
            else:
                log("INFO", f"Already connected: {self.wlan.ifconfig()[0]}")
                led.on()
                return True
        except Exception as e:
            log("ERROR", f"WiFi connect error: {e}")
            return False
    
    def is_connected(self):
        return self.wlan.isconnected()

# ============================================================================
# HTTP CLIENT
# ============================================================================

class HTTPClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.timeout = 5
    
    def post_detection(self, jpeg_bytes, mode="driving", velocity_kmh=None):
        """
        POST image to dual-mode detection endpoint
        
        Returns: dict with detection results or None on error
        """
        try:
            # Create multipart form data
            boundary = b'----FormBoundary'
            body = bytearray()
            
            # Add mode parameter
            body.extend(b'--' + boundary + b'\r\n')
            body.extend(b'Content-Disposition: form-data; name="mode"\r\n\r\n')
            body.extend(mode.encode() + b'\r\n')
            
            # Add velocity parameter (optional)
            if velocity_kmh is not None:
                body.extend(b'--' + boundary + b'\r\n')
                body.extend(b'Content-Disposition: form-data; name="velocity_kmh"\r\n\r\n')
                body.extend(str(velocity_kmh).encode() + b'\r\n')
            
            # Add image file
            body.extend(b'--' + boundary + b'\r\n')
            body.extend(
                b'Content-Disposition: form-data; name="image"; '
                b'filename="frame.jpg"\r\n'
            )
            body.extend(b'Content-Type: image/jpeg\r\n\r\n')
            body.extend(jpeg_bytes)
            body.extend(b'\r\n--' + boundary + b'--\r\n')
            
            # Send request
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.host, self.port))
            
            # HTTP headers
            request = (
                f"POST /detect/dual-mode HTTP/1.1\r\n"
                f"Host: {self.host}:{self.port}\r\n"
                f"Content-Type: multipart/form-data; boundary={boundary.decode()}\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n"
                f"\r\n"
            ).encode()
            
            sock.sendall(request)
            sock.sendall(body)
            
            # Receive response
            response = b""
            while True:
                try:
                    chunk = sock.recv(1024)
                    if not chunk:
                        break
                    response += chunk
                except socket.timeout:
                    break
            
            sock.close()
            
            # Parse JSON response
            try:
                # Find JSON body (after headers)
                parts = response.split(b'\r\n\r\n', 1)
                if len(parts) > 1:
                    json_str = parts[1].decode('utf-8', errors='ignore')
                    result = json.loads(json_str)
                    log("DEBUG", f"Detection result: {result.get('alert', 'N/A')}")
                    return result
            except Exception as e:
                log("ERROR", f"JSON parse error: {e}")
                return None
        
        except Exception as e:
            log("ERROR", f"HTTP POST error: {e}")
            return None

# ============================================================================
# MAIN APPLICATION
# ============================================================================

class DashcamApp:
    def __init__(self):
        self.wifi_mgr = WiFiManager(WIFI_SSID, WIFI_PASSWORD)
        self.http_client = HTTPClient(BACKEND_HOST, BACKEND_PORT)
        self.gps = GPSParser(GPS_UART_NUM, GPS_RX, GPS_TX, GPS_BAUD)
        self.last_frame_time = 0
        self.last_gps_time = 0
    
    def run(self):
        """Main application loop"""
        log("INFO", "=" * 50)
        log("INFO", "PotholeNet ESP32-CAM Dashboard Camera Starting")
        log("INFO", "=" * 50)
        
        # Initialize camera
        if not camera_ctrl.init_camera():
            log("ERROR", "Failed to initialize camera. Halting.")
            return
        
        time.sleep(1)
        log_free_mem()
        
        # Connect to WiFi
        if not self.wifi_mgr.connect():
            log("ERROR", "Failed to connect to WiFi. Retrying...")
            time.sleep(5)
            return
        
        log("INFO", "Ready for detection. Starting capture loop...")
        log("INFO", f"Backend: {BACKEND_URL}")
        
        frame_count = 0
        error_count = 0
        
        try:
            while True:
                current_time = time.time()
                
                # Update GPS data periodically
                if (current_time - self.last_gps_time) > LOCATION_INTERVAL:
                    self.gps.read_sentence()
                    self.last_gps_time = current_time
                
                # Capture and send frame
                if (current_time - self.last_frame_time) > FRAME_INTERVAL:
                    log("DEBUG", f"Capturing frame {frame_count + 1}...")
                    
                    jpeg_data = camera_ctrl.capture_jpeg()
                    if jpeg_data:
                        frame_size = len(jpeg_data)
                        gps_status = self.gps.get_status()
                        velocity = gps_status['velocity_kmh']
                        
                        # Determine mode based on velocity
                        mode = "reverse" if velocity < 0 else "driving"
                        
                        log("INFO", 
                            f"Sending frame {frame_count + 1} "
                            f"({frame_size} bytes, "
                            f"mode={mode}, "
                            f"velocity={velocity:.1f} km/h)")
                        
                        # Send to backend
                        result = self.http_client.post_detection(
                            jpeg_data,
                            mode=mode,
                            velocity_kmh=velocity if velocity != 0 else None
                        )
                        
                        if result:
                            alert = result.get('alert', 'N/A')
                            mode_result = result.get('mode', 'UNKNOWN')
                            log("INFO", f"Alert: {alert} (Mode: {mode_result})")
                            error_count = 0
                            led.pulse()
                        else:
                            error_count += 1
                            log("ERROR", f"Detection failed (error {error_count})")
                            if error_count > 5:
                                log("ERROR", "Too many errors. Reconnecting WiFi...")
                                self.wifi_mgr.connect()
                                error_count = 0
                        
                        frame_count += 1
                        log_free_mem()
                        self.last_frame_time = current_time
                    else:
                        log("ERROR", "Failed to capture frame")
                
                time.sleep(0.1)  # Small delay to prevent busy-waiting
        
        except KeyboardInterrupt:
            log("INFO", "Shutting down...")
        except Exception as e:
            log("ERROR", f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    app = DashcamApp()
    app.run()
