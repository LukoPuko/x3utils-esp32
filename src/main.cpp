// x3utils-esp32 — entry point.
//
// Brings up WiFi (self-hosted hotspot by default, or joins a network), serves
// the web UI, bridges the browser to the SWD operations, and runs the queued
// operation from loop() so the blocking bit-banged SWD never stalls the async
// web stack.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <WiFi.h>

#include "at32.h"
#include "board.h"
#include "config.h"
#include "fw_ident.h"
#include "swd.h"
#include "web_ui.h"
#include "x3_ops.h"

static Swd swd;
static At32 at32(swd);
static X3Ops ops(swd, at32);

static AsyncWebServer server(80);
static AsyncWebSocket ws("/ws");
static Preferences prefs;

// Live settings (loaded from NVS at boot).
struct Settings {
  String wifi = "ap";
  String apSsid = AP_SSID_DEFAULT, apPass = AP_PASSWORD_DEFAULT;
  String staSsid = "", staPass = "";
  int pinClk = PIN_SWCLK_DEFAULT, pinDio = PIN_SWDIO_DEFAULT, pinRst = PIN_NRST_DEFAULT;
  int swdUs = SWD_HALF_CLOCK_US_DEFAULT;
} cfg;

// Upload bookkeeping (raw .bin POST into the shared buffer).
static volatile uint32_t gUploadLen = 0;
static volatile bool gUploadError = false;

// ── Settings persistence ─────────────────────────────────────────────────────
static void loadSettings() {
  prefs.begin("x3cfg", true);
  cfg.wifi = prefs.getString("wifi", cfg.wifi);
  cfg.apSsid = prefs.getString("apSsid", cfg.apSsid);
  cfg.apPass = prefs.getString("apPass", cfg.apPass);
  cfg.staSsid = prefs.getString("staSsid", cfg.staSsid);
  cfg.staPass = prefs.getString("staPass", cfg.staPass);
  cfg.pinClk = prefs.getInt("pinClk", cfg.pinClk);
  cfg.pinDio = prefs.getInt("pinDio", cfg.pinDio);
  cfg.pinRst = prefs.getInt("pinRst", cfg.pinRst);
  cfg.swdUs = prefs.getInt("swdUs", cfg.swdUs);
  prefs.end();
}

static void saveSettings() {
  prefs.begin("x3cfg", false);
  prefs.putString("wifi", cfg.wifi);
  prefs.putString("apSsid", cfg.apSsid);
  prefs.putString("apPass", cfg.apPass);
  prefs.putString("staSsid", cfg.staSsid);
  prefs.putString("staPass", cfg.staPass);
  prefs.putInt("pinClk", cfg.pinClk);
  prefs.putInt("pinDio", cfg.pinDio);
  prefs.putInt("pinRst", cfg.pinRst);
  prefs.putInt("swdUs", cfg.swdUs);
  prefs.end();
}

// ── WiFi ─────────────────────────────────────────────────────────────────────
static void startWifi() {
  if (cfg.wifi == "sta" && cfg.staSsid.length()) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(cfg.staSsid.c_str(), cfg.staPass.c_str());
    Serial.printf("Joining WiFi \"%s\"", cfg.staSsid.c_str());
    uint32_t start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) { delay(300); Serial.print("."); }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
      Serial.print("Joined. IP: "); Serial.println(WiFi.localIP());
      return;
    }
    Serial.println("Join failed — falling back to hotspot.");
  }
  WiFi.mode(WIFI_AP);
  bool open = cfg.apPass.length() < 8;
  WiFi.softAP(cfg.apSsid.c_str(), open ? nullptr : cfg.apPass.c_str());
  Serial.print("Hotspot \""); Serial.print(cfg.apSsid);
  Serial.print("\" up. Connect, then open http://"); Serial.print(WiFi.softAPIP()); Serial.println("/");
}

// ── WebSocket event sink ─────────────────────────────────────────────────────
static void sinkEvent(const OpEvent &e) {
  JsonDocument doc;
  doc["type"] = e.type;
  if (e.type == "log" || e.type == "stage" || e.type == "done") doc["text"] = e.text;
  if (e.type == "done") doc["ok"] = e.ok;
  if (e.type == "progress") { doc["done"] = e.done; doc["total"] = e.total; doc["phase"] = e.phase; }
  if (e.type == "stage") doc["phase"] = e.phase;
  String out;
  serializeJson(doc, out);
  ws.textAll(out);
}

// ── HTTP helpers ─────────────────────────────────────────────────────────────
static OpMode parseMode(const String &s) {
  if (s == "reset") return OpMode::reset;
  if (s == "race") return OpMode::race;
  return OpMode::normal;
}
static OpKind parseKind(const String &s) {
  if (s == "check") return OpKind::check;
  if (s == "dump") return OpKind::dump;
  if (s == "flashFull") return OpKind::flashFull;
  if (s == "flashSlot0") return OpKind::flashSlot0;
  if (s == "protectionCheck") return OpKind::protectionCheck;
  if (s == "rescue") return OpKind::rescue;
  if (s == "compat") return OpKind::compat;
  return OpKind::none;
}

static void sendJson(AsyncWebServerRequest *req, const String &body, int code = 200) {
  req->send(code, "application/json", body);
}

static void routes() {
  server.addHandler(&ws);

  server.on("/", HTTP_GET, [](AsyncWebServerRequest *req) {
    req->send_P(200, "text/html", INDEX_HTML);
  });

  // Start an operation.
  server.on("/api/op", HTTP_POST, [](AsyncWebServerRequest *req) {},
            nullptr,
            [](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total) {
    if (index + len != total) return;  // only act on a complete (single-chunk) body
    JsonDocument doc;
    if (deserializeJson(doc, data, len)) { sendJson(req, "{\"ok\":false,\"why\":\"bad JSON\"}"); return; }
    OpKind kind = parseKind(doc["kind"] | "");
    OpMode mode = parseMode(doc["mode"] | "normal");
    String mcu = doc["mcuModel"] | "";
    if (kind == OpKind::none) { sendJson(req, "{\"ok\":false,\"why\":\"unknown op\"}"); return; }
    String why;
    if (!ops.request(kind, mode, mcu, why)) { sendJson(req, String("{\"ok\":false,\"why\":\"") + why + "\"}"); return; }
    sendJson(req, "{\"ok\":true}");
  });

  // Raw .bin upload into the shared buffer (used before a flash op).
  server.on("/api/upload", HTTP_POST,
            [](AsyncWebServerRequest *req) {
    if (gUploadError) { sendJson(req, "{\"ok\":false,\"why\":\"file too large or device busy\"}"); return; }
    ops.setUploadLength(gUploadLen);
    sendJson(req, String("{\"ok\":true,\"len\":") + gUploadLen + "}");
  },
            nullptr,
            [](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total) {
    if (index == 0) { gUploadLen = 0; gUploadError = ops.busy(); }
    if (gUploadError) return;
    if (total > ops.uploadCapacity() || index + len > ops.uploadCapacity()) { gUploadError = true; return; }
    memcpy(ops.uploadBuffer() + index, data, len);
    gUploadLen = index + len;
  });

  server.on("/api/abort", HTTP_POST, [](AsyncWebServerRequest *req) {
    ops.abort();
    sendJson(req, "{\"ok\":true}");
  });

  server.on("/api/status", HTTP_GET, [](AsyncWebServerRequest *req) {
    JsonDocument doc;
    doc["busy"] = ops.busy();
    doc["haveBackup"] = ops.backupLength() > 0;
    String tn = at32.target().name;
    doc["target"] = (tn.length() && tn != "unknown") ? tn : "no target";
    // X3-Tuner board telemetry (null/false on plain dev boards).
    int vbat = x3board.batteryMillivolts();
    if (vbat >= 0) { doc["vbat"] = vbat; doc["bat"] = x3board.batteryPercent(); }
    doc["usb"] = x3board.usbPresent();
    doc["hasTgtPower"] = x3board.hasTargetPower();
    doc["tgtPower"] = x3board.targetPowered();
    int vtgt = x3board.targetMillivolts();
    if (vtgt >= 0) doc["vtgt"] = vtgt;
    String out; serializeJson(doc, out);
    sendJson(req, out);
  });

  // Switch the board's 3.3 V supply for the VCU (X3-Tuner PCB only).
  server.on("/api/target", HTTP_POST, [](AsyncWebServerRequest *req) {},
            nullptr,
            [](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total) {
    if (index + len != total) return;  // only act on a complete (single-chunk) body
    JsonDocument doc;
    if (deserializeJson(doc, data, len)) { sendJson(req, "{\"ok\":false,\"why\":\"bad JSON\"}"); return; }
    if (ops.busy()) { sendJson(req, "{\"ok\":false,\"why\":\"an operation is running\"}"); return; }
    String why;
    bool ok = x3board.setTargetPower(doc["on"] | false, why);
    JsonDocument res;
    res["ok"] = ok;
    if (!ok) res["why"] = why;
    String out; serializeJson(res, out);
    sendJson(req, out);
  });

  // Backup download. Defaults to the pre-SHU-patch original; ?patched=1 serves
  // the exact bytes now in flash.
  server.on("/api/backup.bin", HTTP_GET, [](AsyncWebServerRequest *req) {
    uint32_t n = ops.backupLength();
    if (!n) { req->send(404, "text/plain", "no backup yet"); return; }
    bool original = !req->hasParam("patched");
    AsyncWebServerResponse *res = req->beginChunkedResponse(
        "application/octet-stream",
        [original](uint8_t *buffer, size_t maxLen, size_t index) -> size_t {
          uint32_t total = ops.backupLength();
          if (index >= total) return 0;
          size_t chunk = total - index < maxLen ? total - index : maxLen;
          for (size_t i = 0; i < chunk; i++) buffer[i] = ops.backupByteAt(index + i, original);
          return chunk;
        });
    res->addHeader("Content-Disposition", "attachment; filename=x3utils-backup.bin");
    req->send(res);
  });

  server.on("/api/settings", HTTP_GET, [](AsyncWebServerRequest *req) {
    JsonDocument doc;
    doc["wifi"] = cfg.wifi;
    doc["apSsid"] = cfg.apSsid;
    doc["apPass"] = cfg.apPass;
    doc["staSsid"] = cfg.staSsid;
    doc["staPass"] = cfg.staPass;
    doc["pinClk"] = cfg.pinClk;
    doc["pinDio"] = cfg.pinDio;
    doc["pinRst"] = cfg.pinRst;
    doc["swdUs"] = cfg.swdUs;
    JsonArray models = doc["mcuModels"].to<JsonArray>();
    for (auto &m : fwident::mcuModels()) models.add(m);
    String out; serializeJson(doc, out);
    sendJson(req, out);
  });

  server.on("/api/settings", HTTP_POST, [](AsyncWebServerRequest *req) {},
            nullptr,
            [](AsyncWebServerRequest *req, uint8_t *data, size_t len, size_t index, size_t total) {
    if (index + len != total) return;  // only act on a complete (single-chunk) body
    JsonDocument doc;
    if (deserializeJson(doc, data, len)) { sendJson(req, "{\"ok\":false}"); return; }
    cfg.wifi = doc["wifi"] | cfg.wifi;
    cfg.apSsid = doc["apSsid"] | cfg.apSsid;
    cfg.apPass = doc["apPass"] | cfg.apPass;
    cfg.staSsid = doc["staSsid"] | cfg.staSsid;
    cfg.staPass = doc["staPass"] | cfg.staPass;
    cfg.pinClk = doc["pinClk"] | cfg.pinClk;
    cfg.pinDio = doc["pinDio"] | cfg.pinDio;
    cfg.pinRst = doc["pinRst"] | cfg.pinRst;
    cfg.swdUs = doc["swdUs"] | cfg.swdUs;
    saveSettings();
    sendJson(req, "{\"ok\":true}");
    delay(300);
    ESP.restart();
  });

  server.onNotFound([](AsyncWebServerRequest *req) { req->send(404, "text/plain", "not found"); });
}

void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\nx3utils-esp32 starting");

  x3board.begin();  // target supply off first thing
  loadSettings();

  if (!ops.begin()) {
    Serial.println("FATAL: could not allocate the 128 KB working buffer.");
  }
  swd.configure(cfg.pinClk, cfg.pinDio, cfg.pinRst, (uint8_t)cfg.swdUs);
  at32.setLog([](const String &l) { OpEvent e; e.type = "log"; e.text = l; sinkEvent(e); });
  ops.setSink(sinkEvent);

  startWifi();
  if (MDNS.begin(MDNS_HOSTNAME)) {
    MDNS.addService("http", "tcp", 80);
    Serial.printf("mDNS: http://%s.local/\n", MDNS_HOSTNAME);
  }
  routes();
  server.begin();
  Serial.println("Web server up on port 80.");
}

void loop() {
  ops.loopTick();
  x3board.loopTick(ops.busy());
  ws.cleanupClients();
  delay(1);
}
