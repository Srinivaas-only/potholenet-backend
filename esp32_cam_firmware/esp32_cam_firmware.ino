// PotholeNet ESP32-CAM firmware.
// Captures a JPEG every FRAME_INTERVAL_MS and POSTs it to the backend.
// Mode (REVERSE / DRIVING) is decided server-side from the phone's GPS state.

#include <WiFi.h>
#include <HTTPClient.h>
#include "esp_camera.h"

// WIFI_SSID, WIFI_PASSWORD, BACKEND_URL come from secrets.h (gitignored).
// Copy secrets.h.example to secrets.h and fill in your values before flashing.
#include "secrets.h"

static const uint32_t FRAME_INTERVAL_MS = 1000;

// AI Thinker ESP32-CAM pin map (OV2640).
#define PWDN_GPIO_NUM   32
#define RESET_GPIO_NUM  -1
#define XCLK_GPIO_NUM    0
#define SIOD_GPIO_NUM   26
#define SIOC_GPIO_NUM   27
#define Y9_GPIO_NUM     35
#define Y8_GPIO_NUM     34
#define Y7_GPIO_NUM     39
#define Y6_GPIO_NUM     36
#define Y5_GPIO_NUM     21
#define Y4_GPIO_NUM     19
#define Y3_GPIO_NUM     18
#define Y2_GPIO_NUM      5
#define VSYNC_GPIO_NUM  25
#define HREF_GPIO_NUM   23
#define PCLK_GPIO_NUM   22

static const char* BOUNDARY = "----PotholeNet";

static void initCamera() {
  camera_config_t c = {};
  c.ledc_channel = LEDC_CHANNEL_0;
  c.ledc_timer   = LEDC_TIMER_0;
  c.pin_d0 = Y2_GPIO_NUM;  c.pin_d1 = Y3_GPIO_NUM;
  c.pin_d2 = Y4_GPIO_NUM;  c.pin_d3 = Y5_GPIO_NUM;
  c.pin_d4 = Y6_GPIO_NUM;  c.pin_d5 = Y7_GPIO_NUM;
  c.pin_d6 = Y8_GPIO_NUM;  c.pin_d7 = Y9_GPIO_NUM;
  c.pin_xclk  = XCLK_GPIO_NUM;
  c.pin_pclk  = PCLK_GPIO_NUM;
  c.pin_vsync = VSYNC_GPIO_NUM;
  c.pin_href  = HREF_GPIO_NUM;
  c.pin_sccb_sda = SIOD_GPIO_NUM;
  c.pin_sccb_scl = SIOC_GPIO_NUM;
  c.pin_pwdn  = PWDN_GPIO_NUM;
  c.pin_reset = RESET_GPIO_NUM;
  c.xclk_freq_hz = 20000000;
  c.pixel_format = PIXFORMAT_JPEG;
  c.frame_size   = FRAMESIZE_VGA;   // 640x480
  c.jpeg_quality = 12;              // 0=best, 63=worst
  c.fb_count     = 2;
  c.grab_mode    = CAMERA_GRAB_LATEST;
  c.fb_location  = CAMERA_FB_IN_PSRAM;

  if (!psramFound()) {
    Serial.println("[WARN] No PSRAM — falling back to DRAM @ SVGA");
    c.frame_size  = FRAMESIZE_SVGA;
    c.fb_location = CAMERA_FB_IN_DRAM;
    c.fb_count    = 1;
  }

  esp_err_t err = esp_camera_init(&c);
  if (err != ESP_OK) {
    Serial.printf("[FATAL] Camera init failed: 0x%x\n", err);
    while (1) delay(1000);
  }
  Serial.println("[OK] Camera initialized");
}

static void connectWiFi() {
  Serial.printf("[INFO] Connecting to '%s'...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED) {
    if (millis() - start > 20000) {
      Serial.println("\n[ERROR] WiFi timeout — restarting");
      ESP.restart();
    }
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[OK] IP=%s RSSI=%d dBm\n",
                WiFi.localIP().toString().c_str(), WiFi.RSSI());
}

static void postFrame(camera_fb_t* fb) {
  HTTPClient http;
  if (!http.begin(BACKEND_URL)) {
    Serial.println("[ERROR] HTTPClient begin failed");
    return;
  }
  http.setTimeout(15000);

  String head = "--" + String(BOUNDARY) + "\r\n"
                "Content-Disposition: form-data; name=\"image\"; filename=\"frame.jpg\"\r\n"
                "Content-Type: image/jpeg\r\n\r\n";
  String tail = "\r\n--" + String(BOUNDARY) + "--\r\n";

  size_t total = head.length() + fb->len + tail.length();
  uint8_t* body = (uint8_t*)malloc(total);
  if (!body) {
    Serial.println("[ERROR] OOM building multipart body");
    http.end();
    return;
  }
  memcpy(body,                                head.c_str(), head.length());
  memcpy(body + head.length(),                fb->buf,      fb->len);
  memcpy(body + head.length() + fb->len,      tail.c_str(), tail.length());

  http.addHeader("Content-Type",
                 String("multipart/form-data; boundary=") + BOUNDARY);
  int code = http.POST(body, total);
  free(body);

  if (code > 0) {
    String resp = http.getString();
    Serial.printf("[OK] HTTP %d  jpeg=%uB  resp=%s\n",
                  code, (unsigned)fb->len, resp.c_str());
  } else {
    Serial.printf("[ERROR] POST failed: %s\n",
                  http.errorToString(code).c_str());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== PotholeNet ESP32-CAM ===");
  initCamera();
  connectWiFi();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WARN] WiFi dropped — reconnecting");
    connectWiFi();
  }

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[ERROR] Frame capture failed");
    delay(500);
    return;
  }
  postFrame(fb);
  esp_camera_fb_return(fb);
  delay(FRAME_INTERVAL_MS);
}
