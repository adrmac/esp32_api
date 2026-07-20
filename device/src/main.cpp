#include <Arduino.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>

#include "build_config.h"

namespace {
constexpr char HOSTNAME[] = "indoor-sky";
constexpr uint32_t WIFI_TIMEOUT_MS = 20000;
constexpr uint32_t WIFI_RETRY_MS = 10000;

WebServer server(80);
uint32_t lastWifiAttemptMs = 0;
bool servicesStarted = false;

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
  char body[768];
  const bool connected = WiFi.status() == WL_CONNECTED;
  snprintf(
      body,
      sizeof(body),
      "{\"firmware_git_sha\":\"%s\",\"firmware_git_dirty\":%s,"
      "\"firmware_build_utc\":\"%s\",\"hostname\":\"%s\","
      "\"uptime_ms\":%lu,\"wifi_connected\":%s,\"ip\":\"%s\","
      "\"wifi_rssi_dbm\":%ld,\"wifi_sleep\":%s,\"free_heap\":%u,\"psram_found\":%s,"
      "\"psram_size\":%u,\"free_psram\":%u,\"ota_ready\":%s}",
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
      servicesStarted ? "true" : "false");
  server.send(200, "application/json", body);
}

void startNetworkServices() {
  if (servicesStarted || WiFi.status() != WL_CONNECTED) return;

  if (!MDNS.begin(HOSTNAME)) {
    Serial.println("mDNS failed; OTA remains available by IP");
  }

  ArduinoOTA.setHostname(HOSTNAME);
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
  connectWifi();
  startNetworkServices();
}

void loop() {
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
