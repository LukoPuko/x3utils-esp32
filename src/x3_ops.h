// High-level x3utils operations, driven by the web UI.
//
// Mirrors the actions of the desktop/web app: Check, Backup (dump), Flash full,
// Flash slot 0, Check protection, Unlock/rescue, and SHU compatible. A web
// handler validates the request and queues ONE command; the blocking SWD work
// runs from loop() (never inside an async callback) and streams log/progress/
// stage/done events back out through the sink set with setSink().

#pragma once

#include <Arduino.h>
#include <functional>
#include <vector>

#include "at32.h"
#include "config.h"  // FLASH_BASE, SLOT0_BASE, BACKUP_LENGTH
#include "swd.h"

enum class OpKind { none, check, dump, flashFull, flashSlot0, protectionCheck, rescue, compat };
enum class OpMode { normal, reset, race };

// Event sink: type is "log" | "progress" | "stage" | "done".
struct OpEvent {
  String type;
  String text;      // log line / stage name / done message
  bool ok = false;  // for "done"
  uint32_t done = 0, total = 0;  // for "progress"
  String phase;                  // for "progress"/"stage"
};
typedef std::function<void(const OpEvent &)> OpSink;

class X3Ops {
 public:
  X3Ops(Swd &swd, At32 &at32) : _swd(swd), _at32(at32) {}

  bool begin();  // allocate the shared 128 KB buffer
  void setSink(OpSink sink) { _sink = sink; }

  // Queue a command. Returns false (with [why]) if one is already running or
  // the request is invalid. [payload]/[payloadLen] is the uploaded image for
  // the flash operations.
  bool request(OpKind kind, OpMode mode, const String &mcuModel, String &why);

  // Upload buffer access for the web layer (flash/slot0 .bin upload).
  uint8_t *uploadBuffer() { return _buf; }
  uint32_t uploadCapacity() const { return BACKUP_LENGTH; }
  void setUploadLength(uint32_t n) { _bufLen = n; }

  // Backup download: fills up to BACKUP_LENGTH bytes; returns valid length, or
  // 0 if no backup is available. [original] restores the pre-SHU-patch bytes.
  uint32_t backupLength() const { return _haveBackup ? BACKUP_LENGTH : 0; }
  uint8_t backupByteAt(uint32_t i, bool original) const;

  bool busy() const { return _running; }
  void abort() { _abort = true; }

  // Called every loop() iteration; executes a queued command.
  void loopTick();

 private:
  bool connect(OpMode mode, TargetInfo &t, String &err);
  void finish(bool ok, const String &msg);
  void log(const String &s);
  void stage(const String &name);
  void progress(const String &phase, uint32_t done, uint32_t total);

  void runCheck(OpMode);
  void runDump(OpMode);
  void runFlash(OpMode, bool slot0);
  void runProtection(OpMode);
  void runRescue(OpMode);
  void runCompat(OpMode, const String &mcuModel);

  Swd &_swd;
  At32 &_at32;
  OpSink _sink = nullptr;

  uint8_t *_buf = nullptr;    // shared 128 KB buffer (dump / upload / compat)
  uint32_t _bufLen = 0;       // valid length for a pending flash
  bool _haveBackup = false;   // _buf holds a valid dump

  // SHU-compat restore: the 16 bytes at 0x1420 before patching.
  bool _compatPatched = false;
  uint8_t _origCompat[16];

  volatile bool _pending = false;
  volatile bool _running = false;
  volatile bool _abort = false;
  OpKind _kind = OpKind::none;
  OpMode _mode = OpMode::normal;
  String _mcuModel;
};
