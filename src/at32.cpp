#include "at32.h"

#include "config.h"  // FLASH_BASE, SLOT0_BASE, BACKUP_LENGTH

// ── Cortex-M debug registers ─────────────────────────────────────────────────
static const uint32_t DHCSR = 0xE000EDF0;
static const uint32_t DEMCR = 0xE000EDFC;
static const uint32_t AIRCR = 0xE000ED0C;
static const uint32_t DBGMCU_CR = 0xE0042004;
static const uint32_t DBGMCU_IDCODE = 0xE0042000;
static const uint32_t CPUID_FPU = 0xE000EF34;

static const uint32_t DBGKEY = 0xA05F0000;
static const uint32_t C_DEBUGEN = 1 << 0;
static const uint32_t C_HALT = 1 << 1;
static const uint32_t C_MASKINTS = 1 << 3;
static const uint32_t S_HALT = 1 << 17;
static const uint32_t VC_CORERESET = 1 << 0;
static const uint32_t AIRCR_SYSRESETREQ = 0x05FA0004;

// ── AT32F415 flash controller ────────────────────────────────────────────────
static const uint32_t AT_BASE = 0x40022000;
static const uint32_t AT_UNLOCK = AT_BASE + 0x04;
static const uint32_t AT_USD_UNLOCK = AT_BASE + 0x08;
static const uint32_t AT_STS = AT_BASE + 0x0C;
static const uint32_t AT_CTRL = AT_BASE + 0x10;
static const uint32_t AT_ADDR = AT_BASE + 0x14;
static const uint32_t FLASH_USD_REG = 0x4002201C;

static const uint32_t KEY1 = 0x45670123;
static const uint32_t KEY2 = 0xCDEF89AB;

static const uint32_t CTRL_FPRGM = 1 << 0;
static const uint32_t CTRL_SECERS = 1 << 1;
static const uint32_t CTRL_USDPRGM = 1 << 4;
static const uint32_t CTRL_USDERS = 1 << 5;
static const uint32_t CTRL_ERSTR = 1 << 6;
static const uint32_t CTRL_OPLK = 1 << 7;
static const uint32_t CTRL_USDULKS = 1 << 9;

static const uint32_t STS_OBF = 1 << 0;
static const uint32_t STS_PRGMERR = 1 << 2;
static const uint32_t STS_EPPERR = 1 << 4;

static const uint32_t CRM_CTRL = 0x40021000;
static const uint32_t CRM_HICKEN = 1 << 0;
static const uint32_t CRM_HICKSTBL = 1 << 1;

static const uint32_t USD_BASE = 0x1FFFF800;
static const uint32_t FAP_UNLOCKED = 0xA5;

// Part table (subset: 128 KB writable parts marked; others reported only).
struct AtPart {
  uint32_t pid;
  const char *name;
  uint32_t flashKB;
  uint32_t pageSize;
  bool tested;
};
static const AtPart kParts[] = {
    {0x70030240, "AT32F415RCT7", 256, 2048, false},
    {0x70030241, "AT32F415CCT7", 256, 2048, false},
    {0x70030242, "AT32F415KCU7-4", 256, 2048, false},
    {0x70030243, "AT32F415RCT7-7", 256, 2048, false},
    {0x7003024c, "AT32F415CCU7", 256, 2048, false},
    {0x700301c4, "AT32F415RBT7", 128, 1024, true},
    {0x700301c5, "AT32F415CBT7", 128, 1024, true},
    {0x700301c6, "AT32F415KBU7-4", 128, 1024, false},
    {0x700301c7, "AT32F415RBT7-7", 128, 1024, false},
    {0x700301cd, "AT32F415CBU7", 128, 1024, false},
    {0x70030108, "AT32F415R8T7", 64, 1024, false},
    {0x70030109, "AT32F415C8T7", 64, 1024, false},
    {0x7003010a, "AT32F415K8U7-4", 64, 1024, false},
};

static bool isCollidingPid(uint32_t pid) {
  return pid == 0x700301c5 || pid == 0x70030240 || pid == 0x70030242;
}

bool At32::connect(ConnectMode mode, TargetInfo &outTarget, String &outError) {
  uint32_t idcode = 0;

  if (mode == ConnectMode::underReset) {
    if (!_swd.hasNrst()) {
      outError = "Under-reset mode needs nRST wired to the configured pin.";
      return false;
    }
    emit("[connect] under-reset: asserting nRST");
    _swd.driveNrst(0);
    delay(20);
    if (!_swd.connect(idcode)) { _swd.driveNrst(1); outError = _swd.lastError(); return false; }
    emit(String("[connect] SWD IDCODE 0x") + String(idcode, HEX));
    // Halt, then arm vector-catch and release reset so the core halts at the
    // reset vector before firmware runs.
    if (!halt()) { _swd.driveNrst(1); outError = "halt under reset failed"; return false; }
    _swd.writeWord(DEMCR, VC_CORERESET);
    _swd.driveNrst(1);
    delay(10);
    if (!waitHalted(1500)) {
      // Fall back to a plain halt; some clone nets won't release cleanly.
      halt();
    }
    _swd.writeWord(DEMCR, 0);
    emit("[connect] core caught at reset vector");
  } else {
    if (!_swd.connect(idcode)) { outError = _swd.lastError(); return false; }
    emit(String("[connect] SWD IDCODE 0x") + String(idcode, HEX));
    if (!halt()) { outError = "could not halt the core"; return false; }
  }

  if (!detect(outTarget)) { outError = _lastError; return false; }
  _target = outTarget;
  freezeWatchdogs();
  emit(String("[target] ") + outTarget.name);
  return true;
}

bool At32::detect(TargetInfo &out) {
  uint32_t idcode = 0;
  _swd.readWord(DBGMCU_IDCODE, idcode);
  out.idcode = idcode;

  const AtPart *match = nullptr;
  for (const auto &p : kParts) {
    if (p.pid == idcode) { match = &p; break; }
  }
  if (match && isCollidingPid(idcode)) {
    uint32_t fpu = 0;
    _swd.readWord(CPUID_FPU, fpu);
    if (fpu != 0) match = nullptr;  // an FPU part collides with this PID — reject
  }

  if (match) {
    out.name = String(match->name) + " (" + match->flashKB + " KB, " + match->pageSize + " B pages)";
    out.family = "AT32";
    out.flashKB = match->flashKB;
    out.pageSize = match->pageSize;
    out.sramBytes = 32 * 1024;
    out.tested = match->tested;
    out.writable = (match->flashKB == 128 && match->pageSize == 1024);
    return true;
  }

  out.family = "unknown";
  out.flashKB = 0;
  out.name = idcode == 0 ? "unknown (DBGMCU IDCODE reads 0)"
                         : String("unsupported target (IDCODE 0x") + String(idcode, HEX) + ")";
  _lastError = "unsupported or unidentified target";
  return false;
}

bool At32::isHalted(bool &halted) {
  uint32_t s;
  if (!_swd.readWord(DHCSR, s)) return false;
  halted = (s & S_HALT) != 0;
  return true;
}

bool At32::halt() {
  return _swd.writeWord(DHCSR, DBGKEY | C_DEBUGEN | C_HALT);
}

bool At32::waitHalted(uint32_t timeoutMs) {
  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    bool h;
    if (isHalted(h) && h) return true;
    delay(2);
  }
  _lastError = "core did not halt in time";
  return false;
}

bool At32::resetHalt() {
  if (!halt()) return false;
  _swd.writeWord(DEMCR, VC_CORERESET);
  _swd.writeWord(DHCSR, DBGKEY | C_DEBUGEN | C_HALT);
  _swd.writeWord(AIRCR, AIRCR_SYSRESETREQ);
  if (!waitHalted(1000)) {
    // Fallback: re-arm and request another reset.
    _swd.writeWord(DEMCR, VC_CORERESET);
    _swd.writeWord(AIRCR, AIRCR_SYSRESETREQ);
    if (!waitHalted(1500)) { _swd.writeWord(DEMCR, 0); return false; }
  }
  _swd.writeWord(DEMCR, 0);
  freezeWatchdogs();
  return true;
}

bool At32::resetRun() {
  _swd.writeWord(DEMCR, 0);
  _swd.writeWord(DHCSR, DBGKEY | C_DEBUGEN);
  return _swd.writeWord(AIRCR, AIRCR_SYSRESETREQ);
}

bool At32::freezeWatchdogs() {
  uint32_t cur;
  if (!_swd.readWord(DBGMCU_CR, cur)) return false;
  return _swd.writeWord(DBGMCU_CR, cur | 0x307);  // freeze WWDG/IWDG/standby/stop/sleep
}

bool At32::readMem(uint32_t addr, uint8_t *dst, uint32_t length) {
  return _swd.readBlock(addr, dst, length);
}

bool At32::waitBusy(uint32_t timeoutMs) {
  uint32_t start = millis();
  for (;;) {
    uint32_t sts;
    if (!_swd.readWord(AT_STS, sts)) { _lastError = "flash STS read failed"; return false; }
    if ((sts & STS_OBF) == 0) return true;
    if (millis() - start > timeoutMs) { _lastError = "flash busy timeout"; return false; }
    delayMicroseconds(200);
  }
}

bool At32::enableHick() {
  uint32_t ctrl;
  if (!_swd.readWord(CRM_CTRL, ctrl)) return false;
  if (ctrl & CRM_HICKSTBL) return true;
  _swd.writeWord(CRM_CTRL, ctrl | CRM_HICKEN);
  uint32_t start = millis();
  while (millis() - start < 1000) {
    _swd.readWord(CRM_CTRL, ctrl);
    if (ctrl & CRM_HICKSTBL) return true;
    delay(2);
  }
  _lastError = "HICK clock did not stabilize";
  return false;
}

bool At32::unlockFlash() {
  uint32_t ctrl;
  _swd.readWord(AT_CTRL, ctrl);
  if ((ctrl & CTRL_OPLK) == 0) return true;
  _swd.writeWord(AT_UNLOCK, KEY1);
  _swd.writeWord(AT_UNLOCK, KEY2);
  _swd.readWord(AT_CTRL, ctrl);
  if (ctrl & CTRL_OPLK) { _lastError = "flash unlock failed (OPLK still set)"; return false; }
  return true;
}

bool At32::unlockUsd() {
  uint32_t ctrl;
  _swd.readWord(AT_CTRL, ctrl);
  if (ctrl & CTRL_USDULKS) return true;
  _swd.writeWord(AT_USD_UNLOCK, KEY1);
  _swd.writeWord(AT_USD_UNLOCK, KEY2);
  _swd.readWord(AT_CTRL, ctrl);
  if ((ctrl & CTRL_USDULKS) == 0) { _lastError = "USD unlock failed"; return false; }
  return true;
}

bool At32::initFlash() {
  if (!enableHick()) return false;
  if (!unlockFlash()) return false;
  if (!unlockUsd()) return false;
  return true;
}

bool At32::deinitFlash() {
  uint32_t ctrl;
  _swd.readWord(AT_CTRL, ctrl);
  if (ctrl & CTRL_USDULKS) _swd.writeWord(AT_CTRL, ctrl & ~CTRL_USDULKS);
  _swd.readWord(AT_CTRL, ctrl);
  if ((ctrl & CTRL_OPLK) == 0) _swd.writeWord(AT_CTRL, ctrl | CTRL_OPLK);
  return true;
}

bool At32::checkErr(uint32_t sts, const char *what) {
  if (sts & STS_EPPERR) { _lastError = "erase/program protection error (EPPERR)"; emit(String("[flash] EPPERR @ ") + what); return false; }
  if (sts & STS_PRGMERR) { _lastError = "programming error (PRGMERR)"; emit(String("[flash] PRGMERR @ ") + what); return false; }
  return true;
}

bool At32::erase(uint32_t addr, uint32_t length, ProgressFn progress) {
  bool h;
  if (!isHalted(h) || !h) { _lastError = "core must be halted to erase"; return false; }
  const uint32_t pageSize = _target.pageSize ? _target.pageSize : 1024;
  uint32_t first = (addr - FLASH_BASE) / pageSize;
  uint32_t last = ((addr + length - FLASH_BASE + pageSize - 1) / pageSize) - 1;
  uint32_t total = last - first + 1;
  if (!initFlash()) return false;
  bool ok = true;
  _swd.writeWord(AT_STS, STS_EPPERR);
  waitBusy(50);
  uint32_t done = 0;
  for (uint32_t page = first; page <= last; page++) {
    uint32_t pageAddr = FLASH_BASE + page * pageSize;
    _swd.writeWord(AT_ADDR, pageAddr);
    _swd.writeWord(AT_CTRL, CTRL_SECERS | CTRL_ERSTR);
    uint32_t sts;
    if (!waitBusy(500)) { ok = false; break; }
    _swd.readWord(AT_STS, sts);
    if (!checkErr(sts, "erase")) { ok = false; break; }
    if (progress) progress(++done, total);
    else done++;
  }
  deinitFlash();
  return ok;
}

bool At32::program(uint32_t addr, const uint8_t *data, uint32_t length, ProgressFn progress) {
  if (addr % 4 != 0) { _lastError = "program address must be word-aligned"; return false; }
  bool h;
  if (!isHalted(h) || !h) { _lastError = "core must be halted to program"; return false; }
  uint32_t padded = (length + 3) & ~3u;
  if (!initFlash()) return false;
  bool ok = true;
  waitBusy(5);
  _swd.writeWord(AT_STS, STS_PRGMERR | STS_EPPERR);
  _swd.writeWord(AT_CTRL, CTRL_FPRGM);
  for (uint32_t off = 0; off < padded; off += 4) {
    uint32_t word = 0xFFFFFFFF;
    // Assemble little-endian word, padding the tail with 0xFF.
    uint8_t b0 = off + 0 < length ? data[off + 0] : 0xFF;
    uint8_t b1 = off + 1 < length ? data[off + 1] : 0xFF;
    uint8_t b2 = off + 2 < length ? data[off + 2] : 0xFF;
    uint8_t b3 = off + 3 < length ? data[off + 3] : 0xFF;
    word = b0 | (b1 << 8) | (b2 << 16) | ((uint32_t)b3 << 24);
    if (word != 0xFFFFFFFF) {
      if (!_swd.writeWord(addr + off, word)) { _lastError = "flash word write failed"; ok = false; break; }
      uint32_t sts;
      if (!waitBusy(5)) { ok = false; break; }
      _swd.readWord(AT_STS, sts);
      if (!checkErr(sts, "program")) { ok = false; break; }
    }
    if (progress && ((off + 4) & 0x3FF) == 0) progress(off + 4, padded);
  }
  _swd.writeWord(AT_CTRL, 0);
  deinitFlash();
  if (ok && progress) progress(padded, padded);
  return ok;
}

bool At32::verify(uint32_t addr, const uint8_t *data, uint32_t length, ProgressFn progress) {
  uint8_t buf[1024];
  uint32_t done = 0;
  while (done < length) {
    uint32_t chunk = length - done < sizeof(buf) ? length - done : sizeof(buf);
    uint32_t readLen = (chunk + 3) & ~3u;
    if (!_swd.readBlock(addr + done, buf, readLen)) { _lastError = "verify read failed"; return false; }
    for (uint32_t i = 0; i < chunk; i++) {
      if (buf[i] != data[done + i]) {
        _lastError = "verify mismatch";
        emit(String("[flash] verify FAILED at 0x") + String(addr + done + i, HEX));
        return false;
      }
    }
    done += chunk;
    if (progress) progress(done, length);
  }
  return true;
}

ProtectionVerdict At32::checkProtection(String &evidenceOut) {
  uint32_t usd = 0, usdOk = _swd.readWord(USD_BASE, usd);
  uint8_t head[16];
  bool flashOk = _swd.readBlock(FLASH_BASE, head, 16);

  uint32_t flashUsd = 0;
  if (_swd.readWord(FLASH_USD_REG, flashUsd)) {
    evidenceOut += "FLASH_USD=0x" + String(flashUsd, HEX) +
                   " FAP=" + String((flashUsd >> 1) & 1) +
                   " FAP_HL=" + String((flashUsd >> 26) & 1) + "  ";
  }

  bool fapRead = usdOk;
  uint32_t fap = fapRead ? (usd & 0xFF) : 0;
  uint32_t fapComp = fapRead ? ((usd >> 8) & 0xFF) : 0;
  bool fapUnlocked = fapRead && fap == FAP_UNLOCKED;
  bool fapCompOk = fapRead && ((fap ^ fapComp) == 0xFF);

  // Classify the flash vector table: MSP-in-SRAM or blank 0xFF is readable;
  // all-0x00 is the masked (protected) signature.
  bool accessible = false, blocked = false;
  if (flashOk) {
    uint32_t w0 = head[0] | (head[1] << 8) | (head[2] << 16) | ((uint32_t)head[3] << 24);
    bool allFf = true, allZero = true;
    for (int i = 0; i < 16; i++) { if (head[i] != 0xFF) allFf = false; if (head[i] != 0x00) allZero = false; }
    if ((w0 & 0xFF000000) == 0x20000000) accessible = true;  // MSP in SRAM
    else if (allFf) accessible = true;                       // blank/erased
    else if (allZero) blocked = true;                        // masked
  }
  evidenceOut += fapRead ? ("USD=0x" + String(usd, HEX)) : "USD unreadable";

  // Same ladder as the desktop/web classifier.
  if (accessible && fapRead && !fapUnlocked) return ProtectionVerdict::notProtected;
  if (fapRead && !fapUnlocked) return ProtectionVerdict::protectedRdp;
  if (fapRead && fapUnlocked && fapCompOk) return ProtectionVerdict::notProtected;
  if (fapRead && fapUnlocked) return blocked ? ProtectionVerdict::protectedRdp : ProtectionVerdict::inconclusive;
  if (accessible) return ProtectionVerdict::notProtected;
  if (blocked) return ProtectionVerdict::protectedRdp;
  return ProtectionVerdict::inconclusive;
}

bool At32::rescueUnlock(String &outError) {
  bool h;
  if (!isHalted(h) || !h) { outError = "core must be halted to rescue"; return false; }
  if (!enableHick()) { outError = _lastError; return false; }

  // Erase phase — FAP is still set, nothing irreversible yet. Match the
  // field-tested raw-register sequence: CTRL=0x220 (USD unlock + USD erase),
  // then 0x260 (start erase).
  if (!unlockFlash()) { _swd.writeWord(AT_CTRL, CTRL_OPLK); outError = _lastError; return false; }
  if (!unlockUsd()) { _swd.writeWord(AT_CTRL, CTRL_OPLK); outError = _lastError; return false; }
  waitBusy(50);
  _swd.writeWord(AT_STS, STS_EPPERR | STS_PRGMERR);
  _swd.writeWord(AT_CTRL, CTRL_USDULKS | CTRL_USDERS);
  _swd.writeWord(AT_CTRL, CTRL_USDULKS | CTRL_USDERS | CTRL_ERSTR);
  if (!waitBusy(1000)) { _swd.writeWord(AT_CTRL, CTRL_OPLK); outError = "USD erase timeout"; return false; }
  uint32_t sts;
  _swd.readWord(AT_STS, sts);
  if (!checkErr(sts, "USD erase")) { _swd.writeWord(AT_CTRL, CTRL_OPLK); outError = _lastError; return false; }
  emit("[protection] user-system-data erased");

  // FAP program phase — the reset zone. On a protected part this write triggers
  // the mass-erase + reset, which tears down SWD mid-write; a fault from here on
  // is the EXPECTED signature of success, so it is tolerated.
  _swd.writeWord(AT_CTRL, CTRL_USDULKS | CTRL_USDPRGM);
  _swd.writeHalf(USD_BASE, 0x5AA5);  // FAP=0xA5 (unlocked), nFAP=0x5A
  waitBusy(1000);
  _swd.writeWord(AT_CTRL, CTRL_OPLK);
  emit("[protection] FAP halfword programmed: 0x5AA5");
  return true;
}
