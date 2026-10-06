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
#if defined(X3_BOARD_TUNER)
// X3-Tuner PCB (hardware/, ESP32-C3-WROOM-02): the SWD trio is on the
// module's left pads, closest to the target header.
static const int PIN_SWCLK_DEFAULT = 5;
static const int PIN_SWDIO_DEFAULT = 6;
static const int PIN_NRST_DEFAULT = 7;
static const int PIN_LED_DEFAULT = 0;
#elif defined(X3_BOARD_C3)
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

// ── X3-Tuner board extras ────────────────────────────────────────────────────
// Only the X3-Tuner PCB has these; on dev boards they are -1 and the matching
// features (battery gauge, switchable target supply) simply report "absent".
#if defined(X3_BOARD_TUNER)
static const int PIN_TGT_EN = 10;      // high = target LDO (3.3 V to the VCU) on
static const int PIN_VTGT_SENSE = 3;   // ADC1: VTGT through a 1:2 divider
static const int PIN_VBAT_SENSE = 4;   // ADC1: battery through a 1:2 divider
static const int PIN_VBUS_SENSE = 1;   // ADC1: VBUS through a 1:2 divider (USB present)
#else
static const int PIN_TGT_EN = -1;
static const int PIN_VTGT_SENSE = -1;
static const int PIN_VBAT_SENSE = -1;
static const int PIN_VBUS_SENSE = -1;
#endif

// A VCU already showing more than this on its 3V3 pin is powered from
// somewhere else; the board then refuses to switch its own supply on.
static const int TARGET_EXTERNAL_MV = 1000;

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
