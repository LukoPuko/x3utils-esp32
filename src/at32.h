// Cortex-M debug control + AT32F415 flash driver for the ESP32 SWD master.
//
// Ported from the x3utils swdart engine (cortexm.dart, targets.dart,
// at32_flash.dart, probe.dart). The flashing *algorithm* is unchanged — the
// register sequences, the mandatory-halt rule, the FAP-rewrite order — only the
// transport is now this ESP32's bit-banged SWD instead of an ST-LINK. The
// experimental SRAM loader is intentionally NOT ported; this uses the
// field-proven direct word-write path.

#pragma once

#include <Arduino.h>
#include <functional>

#include "swd.h"

typedef std::function<void(const String &line)> LogFn;
typedef std::function<void(uint32_t done, uint32_t total)> ProgressFn;

enum class ConnectMode {
  normal,      // plain SWD to a cooperative/service-mode target
  underReset,  // drive nRST low, arm vector catch, release — catches at reset
};

struct TargetInfo {
  String name = "unknown";
  String family = "unknown";
  uint32_t idcode = 0;
  uint32_t flashKB = 0;
  uint32_t pageSize = 0;
  uint32_t sramBytes = 0;
  bool tested = false;
  bool writable = false;  // 128 KB AT32F415 with 1 KB pages
};

// Protection verdict, mirroring the upstream ladder / rdp_check exit codes.
enum class ProtectionVerdict { notProtected, protectedRdp, inconclusive };

class At32 {
 public:
  explicit At32(Swd &swd) : _swd(swd) {}

  void setLog(LogFn fn) { _log = fn; }

  // Connect with the given mode and identify the target. Returns false on any
  // SWD/identity failure; [outError] carries a human message.
  bool connect(ConnectMode mode, TargetInfo &outTarget, String &outError);

  const TargetInfo &target() const { return _target; }

  // Core control.
  bool halt();
  bool isHalted(bool &halted);
  bool waitHalted(uint32_t timeoutMs = 3000);
  bool resetHalt();
  bool resetRun();
  bool freezeWatchdogs();

  // Read a word (debug register or memory) — the upstream "readDebugReg".
  bool readWord(uint32_t addr, uint32_t &out) { return _swd.readWord(addr, out); }

  // Full-flash / block read into [dst] (length bytes).
  bool readMem(uint32_t addr, uint8_t *dst, uint32_t length);

  // ── Flash operations (target must already be halted) ───────────────────────
  // Erase [length] bytes from [addr] (page-aligned internally).
  bool erase(uint32_t addr, uint32_t length, ProgressFn progress = nullptr);
  // Program [data]/[length] at [addr] via direct word writes (skips 0xFFFFFFFF).
  bool program(uint32_t addr, const uint8_t *data, uint32_t length, ProgressFn progress = nullptr);
  // Read-back verify.
  bool verify(uint32_t addr, const uint8_t *data, uint32_t length, ProgressFn progress = nullptr);

  // Protection: read FAP/flash and grade; or destructively clear FAP (rescue).
  ProtectionVerdict checkProtection(String &evidenceOut);
  bool rescueUnlock(String &outError);  // USD erase + FAP=0xA5 rewrite

  const char *lastError() const { return _lastError; }

 private:
  bool detect(TargetInfo &out);
  bool waitBusy(uint32_t timeoutMs);
  bool initFlash();
  bool deinitFlash();
  bool enableHick();
  bool unlockFlash();
  bool unlockUsd();
  bool checkErr(uint32_t sts, const char *what);
  void emit(const String &s) { if (_log) _log(s); }

  Swd &_swd;
  TargetInfo _target;
  LogFn _log = nullptr;
  const char *_lastError = "";
};
