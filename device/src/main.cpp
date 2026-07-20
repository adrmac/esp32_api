#include <Arduino.h>
#include <ArduinoOTA.h>
#include <Adafruit_BME280.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>
#include <Wire.h>
#include <driver/i2s.h>

#include "build_config.h"

namespace {
constexpr char HOSTNAME[] = "indoor-sky";
constexpr uint32_t WIFI_TIMEOUT_MS = 20000;
constexpr uint32_t WIFI_RETRY_MS = 10000;
constexpr uint8_t BME_SCL_PIN = 9;
constexpr uint8_t BME_SDA_PIN = 10;
constexpr i2s_port_t MIC_I2S_PORT = I2S_NUM_0;
constexpr gpio_num_t MIC_SD_PIN = GPIO_NUM_16;
constexpr gpio_num_t MIC_SCK_PIN = GPIO_NUM_17;
constexpr gpio_num_t MIC_WS_PIN = GPIO_NUM_18;
constexpr uint32_t MIC_SAMPLE_RATE = 16000;

WebServer server(80);
Adafruit_BME280 bme;
uint32_t lastWifiAttemptMs = 0;
bool servicesStarted = false;
bool bmeReady = false;
bool micReady = false;
float micRms = 0.0f;
uint32_t micNonzeroSamples = 0;

void startSensors() {
  Wire.begin(BME_SDA_PIN, BME_SCL_PIN);
  bmeReady = bme.begin(0x76, &Wire) || bme.begin(0x77, &Wire);

  const i2s_config_t config = {
      .mode = static_cast<i2s_mode_t>(I2S_MODE_MASTER | I2S_MODE_RX),
      .sample_rate = MIC_SAMPLE_RATE,
      .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
      .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
      .communication_format = I2S_COMM_FORMAT_STAND_I2S,
      .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
      .dma_buf_count = 4,
      .dma_buf_len = 256,
      .use_apll = false,
      .tx_desc_auto_clear = false,
      .fixed_mclk = 0,
  };
  const i2s_pin_config_t pins = {
      .mck_io_num = I2S_PIN_NO_CHANGE,
      .bck_io_num = MIC_SCK_PIN,
      .ws_io_num = MIC_WS_PIN,
      .data_out_num = I2S_PIN_NO_CHANGE,
      .data_in_num = MIC_SD_PIN,
  };
  micReady = i2s_driver_install(MIC_I2S_PORT, &config, 0, nullptr) == ESP_OK &&
             i2s_set_pin(MIC_I2S_PORT, &pins) == ESP_OK;
}

void sampleMic() {
  if (!micReady) return;
  int32_t samples[256];
  size_t bytesRead = 0;
  if (i2s_read(MIC_I2S_PORT, samples, sizeof(samples), &bytesRead, 0) != ESP_OK || bytesRead == 0) return;
  const size_t count = bytesRead / sizeof(samples[0]);
  double sumSquares = 0.0;
  uint32_t nonzero = 0;
  for (size_t i = 0; i < count; ++i) {
    const int32_t sample = samples[i] >> 8;
    if (sample != 0) ++nonzero;
    const double normalized = static_cast<double>(sample) / 8388608.0;
    sumSquares += normalized * normalized;
  }
  micRms = count ? static_cast<float>(sqrt(sumSquares / count)) : 0.0f;
  micNonzeroSamples = nonzero;
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setHostname(HOSTNAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  lastWifiAttemptMs = millis();

  Serial.printf("Connecting to %s", WIFI_SSID);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < WIFI_TIMEOUT_MS) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) WiFi.setSleep(false);
}

void handleStatus() {
  char body[1152];
  const bool connected = WiFi.status() == WL_CONNECTED;
  snprintf(
      body,
      sizeof(body),
      "{\"firmware_git_sha\":\"%s\",\"firmware_git_dirty\":%s,"
      "\"firmware_build_utc\":\"%s\",\"hostname\":\"%s\","
      "\"uptime_ms\":%lu,\"wifi_connected\":%s,\"ip\":\"%s\","
      "\"wifi_rssi_dbm\":%ld,\"wifi_sleep\":%s,\"free_heap\":%u,\"psram_found\":%s,"
      "\"psram_size\":%u,\"free_psram\":%u,\"ota_ready\":%s,"
      "\"bme_ready\":%s,\"bme_temperature_c\":%.3f,\"bme_humidity_pct\":%.3f,"
      "\"bme_pressure_hpa\":%.3f,\"mic_ready\":%s,\"mic_sample_rate_hz\":%lu,"
      "\"mic_rms\":%.7f,\"mic_nonzero_samples\":%lu}",
      FIRMWARE_GIT_SHA,
      FIRMWARE_GIT_DIRTY ? "true" : "false",
      FIRMWARE_BUILD_UTC,
      HOSTNAME,
      static_cast<unsigned long>(millis()),
      connected ? "true" : "false",
      connected ? WiFi.localIP().toString().c_str() : "",
      connected ? static_cast<long>(WiFi.RSSI()) : 0L,
      WiFi.getSleep() ? "true" : "false",
      ESP.getFreeHeap(),
      psramFound() ? "true" : "false",
      ESP.getPsramSize(),
      ESP.getFreePsram(),
      servicesStarted ? "true" : "false",
      bmeReady ? "true" : "false",
      bmeReady ? bme.readTemperature() : 0.0f,
      bmeReady ? bme.readHumidity() : 0.0f,
      bmeReady ? bme.readPressure() / 100.0f : 0.0f,
      micReady ? "true" : "false",
      static_cast<unsigned long>(MIC_SAMPLE_RATE),
      micRms,
      static_cast<unsigned long>(micNonzeroSamples));
  server.send(200, "application/json", body);
}

void startNetworkServices() {
  if (servicesStarted || WiFi.status() != WL_CONNECTED) return;

  if (!MDNS.begin(HOSTNAME)) {
    Serial.println("mDNS failed; OTA remains available by IP");
  }

  ArduinoOTA.setHostname(HOSTNAME);
  ArduinoOTA.setTimeout(30000);
  ArduinoOTA.onStart([]() { Serial.println("OTA start"); });
  ArduinoOTA.onEnd([]() { Serial.println("OTA complete"); });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA error %u\n", error);
  });
  ArduinoOTA.begin();

  server.on("/", []() { server.send(200, "text/plain", "indoor-sky OTA bootstrap\n"); });
  server.on("/status", HTTP_GET, handleStatus);
  server.begin();
  servicesStarted = true;

  Serial.printf("Ready: http://%s.local/status (%s)\n", HOSTNAME, WiFi.localIP().toString().c_str());
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.printf("Firmware %s%s built %s\n", FIRMWARE_GIT_SHA, FIRMWARE_GIT_DIRTY ? "-dirty" : "", FIRMWARE_BUILD_UTC);
  Serial.printf("PSRAM: %s, %u bytes\n", psramFound() ? "yes" : "no", ESP.getPsramSize());
  startSensors();
  connectWifi();
  startNetworkServices();
}

void loop() {
  sampleMic();
  if (WiFi.status() == WL_CONNECTED) {
    startNetworkServices();
    ArduinoOTA.handle();
    server.handleClient();
  } else if (millis() - lastWifiAttemptMs >= WIFI_RETRY_MS) {
    servicesStarted = false;
    connectWifi();
  }
  delay(2);
}
