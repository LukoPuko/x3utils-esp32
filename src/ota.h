// Over-the-air firmware update for the ESP32 itself (not the VCU).
//
// The companion app POSTs a new, signed firmware .bin to /api/ota; the ESP32
// writes it to the spare OTA slot and reboots into it. This is the ONLY update
// path once the USB/serial download mode is locked by an eFuse (see
// hardware/carrier/SECURITY.md): the app updates the device, but nobody can
// read the flash out or flash it over USB.
//
// Authenticity is enforced by Secure Boot v2 in the bootloader, which refuses
// any image that is not signed with your private key — so a wrong or tampered
// .bin simply will not boot. This endpoint only adds a light access check (a
// token, by default the Wi-Fi AP password) so random clients on the network
// cannot push images or waste a flash cycle.
//
// Build-time gated by X3_OTA and needs an OTA-capable partition table (two app
// slots), see platformio.ini [env:x3carrier].

#pragma once

#ifdef X3_OTA

#include <ESPAsyncWebServer.h>
#include <Update.h>

#include "x3_ops.h"

namespace ota {

inline bool g_active = false;   // a write is in progress
inline bool g_error = false;
inline String g_why;

// Register POST /api/ota. `token` must be presented in the X-OTA-Token header
// (empty token => OTA is refused, so an open AP can never be flashed remotely).
inline void registerRoutes(AsyncWebServer &server, X3Ops &ops, String token) {
  server.on(
      "/api/ota", HTTP_POST,
      [](AsyncWebServerRequest *req) {
        bool ok = !g_error && !Update.hasError();
        String body = ok ? "{\"ok\":true}"
                         : String("{\"ok\":false,\"why\":\"") + (g_why.length() ? g_why : String(Update.errorString())) + "\"}";
        AsyncWebServerResponse *res = req->beginResponse(ok ? 200 : 400, "application/json", body);
        res->addHeader("Connection", "close");
        req->send(res);
        g_active = false;
        if (ok) { delay(250); ESP.restart(); }
      },
      nullptr,
      [token, &ops](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total) {
        if (index == 0) {
          g_error = false;
          g_why = "";
          String got = req->hasHeader("X-OTA-Token") ? req->getHeader("X-OTA-Token")->value() : String();
          if (token.isEmpty() || got != token) { g_error = true; g_why = "unauthorized"; return; }
          if (ops.busy()) { g_error = true; g_why = "device busy"; return; }
          g_active = true;
          if (!Update.begin(total ? total : UPDATE_SIZE_UNKNOWN)) { g_error = true; g_why = Update.errorString(); }
        }
        if (g_error) return;
        if (Update.write(data, len) != len) { g_error = true; g_why = Update.errorString(); return; }
        if (index + len == total) {
          if (!Update.end(true)) { g_error = true; g_why = Update.errorString(); }
        }
      });
}

}  // namespace ota

#endif  // X3_OTA
