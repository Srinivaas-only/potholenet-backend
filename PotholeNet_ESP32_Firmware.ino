/*
 * PotholeNet ESP32-CAM Firmware
 * 
 * Purpose: Wi-Fi Access Point mode with MJPEG video streaming and control endpoint.
 * Hardware: AI-Thinker ESP32-CAM (with built-in USB-C if applicable, or USB-to-Serial adapter)
 * 
 * After flashing:
 *   - ESP32 creates Wi-Fi network: SSID "PotholeNet-AP", password "potholenet"
 *   - Phone connects to this network
 *   - Phone browser opens http://192.168.4.1 → shows status page
 *   - Stream available at http://192.168.4.1:81/stream (MJPEG)
 *   - Control endpoint at http://192.168.4.1/control
 *   - Heartbeat at http://192.168.4.1/heartbeat (for app disconnect detection)
 * 
 * Flashing notes:
 *   - Board: "AI Thinker ESP32-CAM" (install ESP32 board package first)
 *   - Upload Speed: 115200
 *   - Flash Frequency: 80MHz
 *   - Partition Scheme: "Huge APP (3MB No OTA / 1MB SPIFFS)"
 *   - During upload, hold GPIO0 → GND on older boards. New USB-C boards auto-reset.
 *   - If upload fails, press the RST button on the board after "Connecting..."
 */

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>
#include "esp_http_server.h"

// =========================
// CONFIG
// =========================
const char* AP_SSID     = "PotholeNet-AP";
const char* AP_PASSWORD = "potholenet";   // min 8 chars
const int   AP_CHANNEL  = 6;
const int   MAX_CLIENTS = 4;

// =========================
// AI-THINKER PIN DEFINITIONS
// =========================
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
#define LED_GPIO_NUM       4   // built-in flash LED

// =========================
// HTTP SERVER HANDLES
// =========================
httpd_handle_t stream_httpd = NULL;
httpd_handle_t control_httpd = NULL;

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY     = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART         = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

// =========================
// STREAM HANDLER (port 81)
// =========================
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t * fb = NULL;
  esp_err_t res = ESP_OK;
  size_t _jpg_buf_len = 0;
  uint8_t * _jpg_buf = NULL;
  char part_buf[64];

  res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("Camera capture failed");
      res = ESP_FAIL;
    } else {
      if (fb->format != PIXFORMAT_JPEG) {
        bool jpeg_converted = frame2jpg(fb, 80, &_jpg_buf, &_jpg_buf_len);
        esp_camera_fb_return(fb);
        fb = NULL;
        if (!jpeg_converted) {
          Serial.println("JPEG compression failed");
          res = ESP_FAIL;
        }
      } else {
        _jpg_buf_len = fb->len;
        _jpg_buf = fb->buf;
      }
    }

    if (res == ESP_OK) {
      size_t hlen = snprintf((char *)part_buf, 64, STREAM_PART, _jpg_buf_len);
      res = httpd_resp_send_chunk(req, (const char *)part_buf, hlen);
    }
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char *)_jpg_buf, _jpg_buf_len);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));

    if (fb) {
      esp_camera_fb_return(fb);
      fb = NULL;
      _jpg_buf = NULL;
    } else if (_jpg_buf) {
      free(_jpg_buf);
      _jpg_buf = NULL;
    }
    if (res != ESP_OK) break;
  }
  return res;
}

// =========================
// CONTROL HANDLER (port 80)
// =========================
static esp_err_t control_handler(httpd_req_t *req) {
  char query[100];
  if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK) {
    Serial.printf("Control query: %s\n", query);

    char param[32];
    // LED control: /control?led=on or /control?led=off
    if (httpd_query_key_value(query, "led", param, sizeof(param)) == ESP_OK) {
      if (strcmp(param, "on") == 0) {
        digitalWrite(LED_GPIO_NUM, HIGH);
      } else {
        digitalWrite(LED_GPIO_NUM, LOW);
      }
    }
    // Reserved for future: servo, buzzer, etc.
    // if (httpd_query_key_value(query, "servo", param, sizeof(param)) == ESP_OK) { ... }
  }

  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_sendstr(req, "{\"status\":\"ok\"}");
  return ESP_OK;
}

// =========================
// HEARTBEAT HANDLER
// =========================
static esp_err_t heartbeat_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  char buf[80];
  snprintf(buf, sizeof(buf), "{\"alive\":true,\"uptime\":%lu,\"clients\":%d}",
           millis() / 1000, WiFi.softAPgetStationNum());
  httpd_resp_sendstr(req, buf);
  return ESP_OK;
}

// =========================
// STATUS PAGE HANDLER (root)
// =========================
static esp_err_t index_handler(httpd_req_t *req) {
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  const char* html =
    "<!DOCTYPE html><html><head><title>PotholeNet ESP32-CAM</title>"
    "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:20px;}"
    "h1{color:#22c55e;}a{color:#22d3ee;}.box{background:#222;padding:16px;border-radius:8px;margin:12px 0;}</style>"
    "</head><body>"
    "<h1>PotholeNet ESP32-CAM</h1>"
    "<div class='box'><b>Status:</b> Online</div>"
    "<div class='box'><b>Stream URL:</b><br><a href='http://192.168.4.1:81/stream'>http://192.168.4.1:81/stream</a></div>"
    "<div class='box'><b>App URL:</b><br>Open the PotholeNet app on your phone</div>"
    "<div class='box'><b>Hardware:</b> AI-Thinker ESP32-CAM<br><b>Mode:</b> Wi-Fi Access Point</div>"
    "</body></html>";
  httpd_resp_sendstr(req, html);
  return ESP_OK;
}

// =========================
// SERVER STARTUP
// =========================
void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  config.ctrl_port   = 32768;

  httpd_uri_t index_uri = {
    .uri = "/", .method = HTTP_GET, .handler = index_handler, .user_ctx = NULL
  };
  httpd_uri_t control_uri = {
    .uri = "/control", .method = HTTP_GET, .handler = control_handler, .user_ctx = NULL
  };
  httpd_uri_t led_uri = {
    .uri = "/led", .method = HTTP_GET, .handler = control_handler, .user_ctx = NULL
  };
  httpd_uri_t heartbeat_uri = {
    .uri = "/heartbeat", .method = HTTP_GET, .handler = heartbeat_handler, .user_ctx = NULL
  };

  if (httpd_start(&control_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(control_httpd, &index_uri);
    httpd_register_uri_handler(control_httpd, &control_uri);
    httpd_register_uri_handler(control_httpd, &led_uri);
    httpd_register_uri_handler(control_httpd, &heartbeat_uri);
  }

  // Stream server on port 81
  config.server_port = 81;
  config.ctrl_port   = 32769;
  httpd_uri_t stream_uri = {
    .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL
  };
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

// =========================
// SETUP
// =========================
void setup() {
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  pinMode(LED_GPIO_NUM, OUTPUT);
  digitalWrite(LED_GPIO_NUM, LOW);

  // Camera config
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_VGA;       // 640x480
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;                // 0-63, lower = higher quality
  config.fb_count = 2;

  if (psramFound()) {
    config.jpeg_quality = 10;
    config.fb_count = 2;
    config.grab_mode = CAMERA_GRAB_LATEST;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while (true) {
      digitalWrite(LED_GPIO_NUM, HIGH);
      delay(200);
      digitalWrite(LED_GPIO_NUM, LOW);
      delay(200);
    }
  }

  sensor_t * s = esp_camera_sensor_get();
  s->set_framesize(s, FRAMESIZE_VGA);
  s->set_brightness(s, 0);
  s->set_saturation(s, 0);
  s->set_vflip(s, 1);   // flip vertically — rear camera mounting
  s->set_hmirror(s, 1); // mirror horizontally — driver expects mirrored rear view

  // Start Wi-Fi AP
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, AP_PASSWORD, AP_CHANNEL, 0, MAX_CLIENTS);
  IPAddress IP = WiFi.softAPIP();

  Serial.println();
  Serial.println("======================================");
  Serial.println("  PotholeNet ESP32-CAM Started");
  Serial.println("======================================");
  Serial.printf("  SSID:     %s\n", AP_SSID);
  Serial.printf("  Password: %s\n", AP_PASSWORD);
  Serial.printf("  IP:       %s\n", IP.toString().c_str());
  Serial.printf("  Stream:   http://%s:81/stream\n", IP.toString().c_str());
  Serial.printf("  Control:  http://%s/control\n", IP.toString().c_str());
  Serial.println("======================================");

  startCameraServer();

  // Blink LED 3x to indicate ready
  for (int i = 0; i < 3; i++) {
    digitalWrite(LED_GPIO_NUM, HIGH);
    delay(150);
    digitalWrite(LED_GPIO_NUM, LOW);
    delay(150);
  }
}

void loop() {
  // Heartbeat blink every 3 seconds — confirms board is alive
  static unsigned long lastBlink = 0;
  if (millis() - lastBlink > 3000) {
    digitalWrite(LED_GPIO_NUM, HIGH);
    delay(30);
    digitalWrite(LED_GPIO_NUM, LOW);
    lastBlink = millis();
  }
  delay(100);
}
