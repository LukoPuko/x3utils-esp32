// x3utils-esp32 — build-time configuration.
//
// Pins, WiFi defaults, and SWD timing live here so a user only edits one file.
// Every value can also be changed at runtime from the web UI (Settings panel);
// the values here are the power-on defaults.

#pragma once

#include <Arduino.h>

// ── SWD wiring ───────────────────────────────────────────────────────────────
// Connect these ESP32 GPIOs to the VCU debug header:
//   SWCLK  -> chip SWCLK
//   SWDIO  -> chip SWDIO
//   NRST   -> chip nRST / C45 (optional but strongly recommended)
//   GND    -> common ground (ALWAYS)
//
// Use 3.3 V logic only. Power the VCU from ONE source at a time (main/bench
// power OR the ESP32 3V3 pin) exactly as the upstream x3utils wiki warns.
#if defined(X3_BOARD_C3)
static const int PIN_SWCLK_DEFAULT = 4;
static const int PIN_SWDIO_DEFAULT = 5;
static const int PIN_NRST_DEFAULT = 6;
static const int PIN_LED_DEFAULT = 8;
#elif defined(X3_BOARD_S3)
static const int PIN_SWCLK_DEFAULT = 4;
static const int PIN_SWDIO_DEFAULT = 5;
static const int PIN_NRST_DEFAULT = 6;
static const int PIN_LED_DEFAULT = 48;
#else  // classic ESP32
static const int PIN_SWCLK_DEFAULT = 18;
static const int PIN_SWDIO_DEFAULT = 19;
static const int PIN_NRST_DEFAULT = 21;
static const int PIN_LED_DEFAULT = 2;
#endif

// Half-clock delay for the bit-banged SWD line, in microseconds. 0 lets the
// line run as fast as the GPIO API allows (a few hundred kHz on a classic
// ESP32), which is reliable for short cables. Raise to 1–3 if a long or noisy
// cable throws "SWD: no ACK" / parity errors.
static const uint8_t SWD_HALF_CLOCK_US_DEFAULT = 0;

// ── WiFi ─────────────────────────────────────────────────────────────────────
// Default is a self-hosted access point so the iPhone just joins the ESP32's
// own network — no router, no internet. Connect to this SSID, then open
// http://192.168.4.1/ in Safari (or any browser).
//
// You can instead join an existing WiFi from the Settings panel; the choice is
// stored in flash and used on the next boot.
static const char AP_SSID_DEFAULT[] = "x3utils-esp32";
static const char AP_PASSWORD_DEFAULT[] = "x3utils123";  // >= 8 chars, or "" for open
static const char MDNS_HOSTNAME[] = "x3utils";           // http://x3utils.local/

// ── Target geometry (AT32F415, 128 KB) ───────────────────────────────────────
static const uint32_t FLASH_BASE = 0x08000000UL;
static const uint32_t SLOT0_BASE = 0x08001000UL;
static const uint32_t BACKUP_LENGTH = 131072UL;  // 128 KB — the only backup size
