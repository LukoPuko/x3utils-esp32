#include "x3_ops.h"

#include "board.h"
#include "config.h"
#include "fw_ident.h"

#if defined(BOARD_HAS_PSRAM) || defined(CONFIG_SPIRAM)
#include <esp_heap_caps.h>
#endif

bool X3Ops::begin() {
  // Prefer PSRAM for the big buffer; fall back to internal heap.
  _buf = (uint8_t *)ps_malloc(BACKUP_LENGTH);
  if (!_buf) _buf = (uint8_t *)malloc(BACKUP_LENGTH);
  if (!_buf) return false;
  memset(_buf, 0xFF, BACKUP_LENGTH);
  return true;
}

void X3Ops::log(const String &s) {
  if (_sink) { OpEvent e; e.type = "log"; e.text = s; _sink(e); }
}
void X3Ops::stage(const String &name) {
  if (_sink) { OpEvent e; e.type = "stage"; e.text = name; e.phase = name; _sink(e); }
}
void X3Ops::progress(const String &phase, uint32_t done, uint32_t total) {
  if (_sink) { OpEvent e; e.type = "progress"; e.phase = phase; e.done = done; e.total = total; _sink(e); }
}
void X3Ops::finish(bool ok, const String &msg) {
  if (_sink) { OpEvent e; e.type = "done"; e.ok = ok; e.text = msg; _sink(e); }
}

uint8_t X3Ops::backupByteAt(uint32_t i, bool original) const {
  if (i >= BACKUP_LENGTH) return 0xFF;
  if (original && _compatPatched && i >= 0x1420 && i < 0x1430) return _origCompat[i - 0x1420];
  return _buf[i];
}

bool X3Ops::request(OpKind kind, OpMode mode, const String &mcuModel, String &why) {
  if (_running || _pending) { why = "Another operation is already running."; return false; }
  if ((kind == OpKind::flashFull || kind == OpKind::flashSlot0)) {
    if (_bufLen == 0) { why = "No firmware uploaded."; return false; }
    if (kind == OpKind::flashFull && _bufLen != BACKUP_LENGTH) {
      why = "Full-image flash needs exactly 131072 bytes."; return false;
    }
    if (kind == OpKind::flashSlot0 && _bufLen > BACKUP_LENGTH - (SLOT0_BASE - FLASH_BASE)) {
      why = "Slot-0 image is too large."; return false;
    }
  }
  _kind = kind;
  _mode = mode;
  _mcuModel = mcuModel;
  _abort = false;
  _pending = true;
  return true;
}

bool X3Ops::connect(OpMode mode, TargetInfo &t, String &err) {
  if (mode == OpMode::race) {
    // On the X3-Tuner PCB the tool switches the VCU's 3.3 V itself, so the
    // race starts exactly at power-on instead of relying on a human hand.
    bool autoPower = x3board.hasTargetPower();
    if (autoPower && !x3board.targetPowered() && x3board.targetMillivolts() > TARGET_EXTERNAL_MV) {
      log("[race] VCU is powered from another source — power-cycle it by hand.");
      autoPower = false;
    }
    if (autoPower) {
      log("[race] switching the VCU supply off and letting it discharge…");
      if (!x3board.dischargeTarget(3000)) log("[race] VCU rail still above 0.3 V — continuing anyway");
      delay(200);
      log("[race] powering the VCU and hammering connect. Press Abort to stop.");
    } else {
      log("[race] applying power now — hammering connect. Press Abort to stop.");
    }
    uint32_t attempt = 0;
    for (;;) {
      if (_abort) { err = "aborted"; return false; }
      attempt++;
      if (autoPower && attempt == 1) {
        String why;
        // External supply was ruled out above; what is left is our own charge.
        if (!x3board.setTargetPower(true, why, true)) { err = why; return false; }
      }
      if (_at32.connect(ConnectMode::normal, t, err)) {
        log(String("== caught on attempt ") + attempt + " ==");
        return true;
      }
      _swd.release();
      if (attempt % 25 == 0) log(String("[race] ") + attempt + " attempts…");
      delay(1);
    }
  }
  ConnectMode cm = (mode == OpMode::reset) ? ConnectMode::underReset : ConnectMode::normal;
  return _at32.connect(cm, t, err);
}

void X3Ops::loopTick() {
  if (!_pending) return;
  _pending = false;
  _running = true;
  OpKind k = _kind;
  OpMode m = _mode;
  switch (k) {
    case OpKind::check: runCheck(m); break;
    case OpKind::dump: runDump(m); break;
    case OpKind::flashFull: runFlash(m, false); break;
    case OpKind::flashSlot0: runFlash(m, true); break;
    case OpKind::protectionCheck: runProtection(m); break;
    case OpKind::rescue: runRescue(m); break;
    case OpKind::compat: runCompat(m, _mcuModel); break;
    default: break;
  }
  _swd.release();
  _running = false;
}

static bool isSingleByte(const uint8_t *b, uint32_t n) {
  for (uint32_t i = 1; i < n; i++) if (b[i] != b[0]) return false;
  return true;
}

void X3Ops::runCheck(OpMode m) {
  stage("Connecting");
  TargetInfo t;
  String err;
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  uint32_t usd;
  if (_at32.readWord(0x4002201CUL, usd)) {
    log(String("[check] FLASH_USD=0x") + String(usd, HEX) + " FAP=" + String((usd >> 1) & 1));
  }
  finish(true, String("Connected: ") + t.name);
}

void X3Ops::runDump(OpMode m) {
  stage("Connecting");
  TargetInfo t;
  String err;
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  if (t.flashKB != 128) { finish(false, String("Backup needs a 128 KB AT32F415; detected ") + t.flashKB + " KB."); return; }
  _haveBackup = false;
  _compatPatched = false;
  stage("Reading 128 KB");
  log("[dump] reading 131072 bytes from 0x08000000");
  // Read in 8 KB chunks so progress updates and the watchdog stays fed.
  const uint32_t CHUNK = 8192;
  for (uint32_t off = 0; off < BACKUP_LENGTH; off += CHUNK) {
    if (_abort) { finish(false, "Aborted."); return; }
    if (!_swd.readBlock(FLASH_BASE + off, _buf + off, CHUNK)) { finish(false, String("Read failed: ") + _swd.lastError()); return; }
    progress("read", off + CHUNK, BACKUP_LENGTH);
    delay(0);
  }
  if (isSingleByte(_buf, BACKUP_LENGTH)) {
    log("[dump] WARNING: image is a single repeated byte (read-protected or blank?)");
    finish(false, "Dump is a single repeated byte — not a usable backup (read-protected? run Check protection).");
    return;
  }
  _haveBackup = true;
  log(String("[dump] identity: ") + fwident::describe(_buf, BACKUP_LENGTH));
  finish(true, "Backup complete — 131072 bytes. Download it from the Backup panel.");
}

void X3Ops::runFlash(OpMode m, bool slot0) {
  stage("Connecting");
  TargetInfo t;
  String err;
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  if (!t.writable) { finish(false, String("Writing needs a 128 KB AT32F415 (1 KB pages); detected ") + t.name); return; }

  uint32_t base = slot0 ? SLOT0_BASE : FLASH_BASE;
  uint32_t len = slot0 ? _bufLen : BACKUP_LENGTH;

  stage("Erasing");
  if (!_at32.erase(base, len, [this](uint32_t d, uint32_t tot) { progress("erase", d, tot); })) {
    finish(false, String("Erase failed: ") + _at32.lastError());
    return;
  }
  log("[flash] erased");
  stage("Writing");
  if (!_at32.program(base, _buf, len, [this](uint32_t d, uint32_t tot) { progress("write", d, tot); })) {
    finish(false, String("Write failed: ") + _at32.lastError());
    return;
  }
  log(String("[flash] wrote ") + len + " bytes");
  stage("Verifying");
  if (!_at32.verify(base, _buf, len, [this](uint32_t d, uint32_t tot) { progress("verify", d, tot); })) {
    finish(false, String("Verify failed: ") + _at32.lastError());
    return;
  }
  log("[flash] verified");
  _at32.resetRun();
  log("[target] reset, running");
  finish(true, slot0 ? "Slot 0 flashed and verified." : "Full image flashed and verified.");
}

void X3Ops::runProtection(OpMode m) {
  stage("Connecting");
  TargetInfo t;
  String err;
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  stage("Reading protection");
  String evidence;
  ProtectionVerdict v = _at32.checkProtection(evidence);
  log(String("[protection] ") + evidence);
  switch (v) {
    case ProtectionVerdict::notProtected: finish(true, "NOT read-protected — flash is readable."); break;
    case ProtectionVerdict::protectedRdp: finish(true, "READ PROTECTED (FAP enabled). Use Unlock/Rescue to clear it (this mass-erases)."); break;
    default: finish(false, "INCONCLUSIVE — signals disagree or the target could not be read reliably."); break;
  }
}

void X3Ops::runRescue(OpMode m) {
  stage("Connecting");
  TargetInfo t;
  String err;
  // Rescue wants the under-reset catch when nRST is available.
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  stage("Unlocking");
  String rerr;
  if (!_at32.rescueUnlock(rerr)) { finish(false, String("Rescue failed: ") + rerr); return; }
  finish(true, "FAP cleared — the chip mass-erased its flash and reset. Power-cycle, reconnect, then Check protection and Flash Only a known-good image.");
}

void X3Ops::runCompat(OpMode m, const String &mcuModel) {
  stage("Connecting");
  TargetInfo t;
  String err;
  if (!connect(m, t, err)) { finish(false, String("Connect failed: ") + err); return; }
  if (!t.writable) { finish(false, String("SHU compat needs a writable 128 KB AT32F415; detected ") + t.name); return; }

  // Step 1 — read current firmware (this is also the safety backup).
  _haveBackup = false;
  _compatPatched = false;
  stage("Backing up");
  const uint32_t CHUNK = 8192;
  for (uint32_t off = 0; off < BACKUP_LENGTH; off += CHUNK) {
    if (_abort) { finish(false, "Aborted."); return; }
    if (!_swd.readBlock(FLASH_BASE + off, _buf + off, CHUNK)) { finish(false, String("Backup read failed: ") + _swd.lastError()); return; }
    progress("read", off + CHUNK, BACKUP_LENGTH);
    delay(0);
  }
  if (isSingleByte(_buf, BACKUP_LENGTH)) { finish(false, "Chip did not read back as firmware (read-protected?). Nothing written."); return; }
  _haveBackup = true;
  log("[compat] original backup captured — download it from the Backup panel before relying on it.");

  // Step 2 — identity + version gates (same as desktop/web).
  stage("Identifying");
  fwident::CompatGate gate = fwident::evaluateCompat(_buf, BACKUP_LENGTH, mcuModel);
  log(String("[compat] ") + gate.message);
  if (!gate.ok) { finish(false, gate.message + " (Backup was saved.)"); return; }
  log(String("[compat] installed: ") + gate.model + " " + gate.type + " " + gate.version);

  // Step 3 — patch in place (saving the original 16 bytes for a clean restore).
  stage("Patching");
  for (int i = 0; i < 16; i++) _origCompat[i] = _buf[0x1420 + i];
  if (!fwident::applyCompatPatch(_buf, BACKUP_LENGTH)) { finish(false, "Patch failed — chip NOT written."); return; }
  _compatPatched = true;
  log("[compat] SHU signature written at 0x1420");

  // Step 4 — flash the patched image back.
  stage("Erasing");
  if (!_at32.erase(FLASH_BASE, BACKUP_LENGTH, [this](uint32_t d, uint32_t tot) { progress("erase", d, tot); })) {
    finish(false, String("Erase failed: ") + _at32.lastError());
    return;
  }
  stage("Writing");
  if (!_at32.program(FLASH_BASE, _buf, BACKUP_LENGTH, [this](uint32_t d, uint32_t tot) { progress("write", d, tot); })) {
    finish(false, String("Write failed: ") + _at32.lastError() + " — the original backup is downloadable.");
    return;
  }
  stage("Verifying");
  if (!_at32.verify(FLASH_BASE, _buf, BACKUP_LENGTH, [this](uint32_t d, uint32_t tot) { progress("verify", d, tot); })) {
    finish(false, String("Verify failed: ") + _at32.lastError());
    return;
  }
  _at32.resetRun();
  finish(true, "SHU-compatible firmware flashed and verified. Original backup is downloadable.");
}
