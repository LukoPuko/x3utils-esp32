// Firmware identification + SHU-compat safety gates.
//
// Ported from the x3utils engine (firmware.dart CompatPatch/CompatXtea,
// device_spec.dart banner rules, fw_version.dart version scanner). SHU compat
// rewrites the controller, so these gates — XTEA-present, not-factory,
// unsupported model, blacklisted/unknown version — refuse exactly what the
// desktop/web app refuses, on the same evidence read from the same offsets.

#pragma once

#include <Arduino.h>
#include <vector>

namespace fwident {

static const uint32_t COMPAT_OFFSET = 0x1420;   // SHU signature (16 bytes)
static const uint32_t RAND_OFFSET = 0x1430;     // device rand (6 bytes)
static const uint32_t XTEA_OFFSET = 0x1440;     // OEM XTEA field (16 bytes)
static const uint32_t SLOT_BANNER_OFFSET = 0x1400;  // banner in a full dump
static const uint32_t SLOT0_OFFSET = 0x1000;        // slot 0 inside a full dump
static const uint32_t SLOT0_REGION_END = 0x10000;

// The fixed 16-byte SHU-compatibility signature.
extern const uint8_t kCompatSignature[16];

// Write the signature at COMPAT_OFFSET; returns false if the image is too short.
bool applyCompatPatch(uint8_t *image, size_t len);

// Result of the full SHU-compat decision over a 128 KB dump.
struct CompatGate {
  bool ok = false;      // true -> patching may proceed
  String message;       // refusal reason (when !ok) or an identity summary
  String model;         // zt3/g3/f3/gt3
  String type;          // VCU/MCU
  String version;       // e.g. "1.5.5" when identified
  String banner;        // raw banner string if present
};

// Decide whether SHU compat may run against [dump]/[len] (a 128 KB backup).
// [declaredMcuModel] is used only when the banner says MCU (MCU carries no
// model of its own); ignored for VCU. Pass "" if unknown.
CompatGate evaluateCompat(const uint8_t *dump, size_t len, const String &declaredMcuModel);

// Human identity line for any dump (used on the Backup result screen too).
String describe(const uint8_t *dump, size_t len);

// The MCU models the UI should offer (derived from the version matrix).
std::vector<String> mcuModels();

}  // namespace fwident
