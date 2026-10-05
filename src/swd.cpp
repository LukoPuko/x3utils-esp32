#include "swd.h"

// MEM-AP register offsets (bank 0).
static const uint8_t AP_CSW = 0x00;
static const uint8_t AP_TAR = 0x04;
static const uint8_t AP_DRW = 0x0C;

// DP register addresses (A[3:2]).
static const uint8_t DP_IDCODE = 0x00;  // read
static const uint8_t DP_ABORT = 0x00;   // write
static const uint8_t DP_CTRLSTAT = 0x04;
static const uint8_t DP_SELECT = 0x08;  // write
static const uint8_t DP_RDBUFF = 0x0C;  // read

// CSW: standard Cortex-M defaults (MasterType=Debug, HPROT=1, SPIDEN) with the
// size field in the low bits. AddrInc = single (0b01) in bits [5:4].
static const uint32_t CSW_BASE = 0x23000050;
static const uint32_t CSW_SIZE_BYTE = 0x0;
static const uint32_t CSW_SIZE_HALF = 0x1;
static const uint32_t CSW_SIZE_WORD = 0x2;

static const int WAIT_RETRIES = 80;

void Swd::configure(int pinSwclk, int pinSwdio, int pinNrst, uint8_t halfClockUs) {
  _pinSwclk = pinSwclk;
  _pinSwdio = pinSwdio;
  _pinNrst = pinNrst;
  _halfClockUs = halfClockUs;
  pinMode(_pinSwclk, OUTPUT);
  digitalWrite(_pinSwclk, LOW);
  dioOut();
  digitalWrite(_pinSwdio, HIGH);
  if (_pinNrst >= 0) {
    // Released by default (input = high-Z, pulled up by the target net).
    pinMode(_pinNrst, INPUT);
  }
}

inline void Swd::delayHalf() {
  if (_halfClockUs) delayMicroseconds(_halfClockUs);
}

void Swd::dioOut() {
  pinMode(_pinSwdio, OUTPUT);
  _dioIsOut = true;
}

void Swd::dioIn() {
  pinMode(_pinSwdio, INPUT);
  _dioIsOut = false;
}

// Host drives SWDIO; target samples on the rising edge.
inline void Swd::writeBit(uint8_t bit) {
  digitalWrite(_pinSwdio, bit ? HIGH : LOW);
  digitalWrite(_pinSwclk, LOW);
  delayHalf();
  digitalWrite(_pinSwclk, HIGH);
  delayHalf();
}

// Target drives SWDIO; host samples while the clock is low, then rises.
inline uint8_t Swd::readBit() {
  digitalWrite(_pinSwclk, LOW);
  delayHalf();
  uint8_t b = digitalRead(_pinSwdio) ? 1 : 0;
  digitalWrite(_pinSwclk, HIGH);
  delayHalf();
  return b;
}

// One clock with SWDIO in its current (released) state — used for turnaround
// and idle.
inline void Swd::clockPulse() {
  digitalWrite(_pinSwclk, LOW);
  delayHalf();
  digitalWrite(_pinSwclk, HIGH);
  delayHalf();
}

void Swd::writeBits(uint32_t value, uint8_t count) {
  for (uint8_t i = 0; i < count; i++) {
    writeBit(value & 1);
    value >>= 1;
  }
}

uint32_t Swd::readBits(uint8_t count) {
  uint32_t value = 0;
  for (uint8_t i = 0; i < count; i++) {
    if (readBit()) value |= (1UL << i);
  }
  return value;
}

void Swd::turnaround() {
  // One clock with the line released, to hand the bus over.
  clockPulse();
}

void Swd::lineReset() {
  dioOut();
  digitalWrite(_pinSwdio, HIGH);
  for (int i = 0; i < 60; i++) clockPulse();  // >= 50 clocks, SWDIO high
}

void Swd::idleCycles(uint8_t n) {
  dioOut();
  digitalWrite(_pinSwdio, LOW);
  for (uint8_t i = 0; i < n; i++) clockPulse();
}

static inline uint8_t parity32(uint32_t v) {
  v ^= v >> 16;
  v ^= v >> 8;
  v ^= v >> 4;
  v ^= v >> 2;
  v ^= v >> 1;
  return v & 1;
}

uint8_t Swd::transfer(bool apnDp, bool isRead, uint8_t a23, uint32_t &data) {
  // a23 carries addr bits [3:2] already shifted into [3:2] position of the
  // request (values 0x0/0x4/0x8/0xC).
  const uint8_t a2 = (a23 >> 2) & 1;
  const uint8_t a3 = (a23 >> 3) & 1;
  const uint8_t req_parity = (apnDp ? 1 : 0) ^ (isRead ? 1 : 0) ^ a2 ^ a3;

  for (int attempt = 0; attempt < WAIT_RETRIES; attempt++) {
    dioOut();
    // Request byte, LSB first: Start=1, APnDP, RnW, A2, A3, Parity, Stop=0, Park=1.
    uint8_t req = 0x81;  // start(bit0) + park(bit7)
    if (apnDp) req |= 1 << 1;
    if (isRead) req |= 1 << 2;
    req |= a2 << 3;
    req |= a3 << 4;
    req |= req_parity << 5;
    writeBits(req, 8);

    // Turnaround, then 3-bit ACK driven by the target.
    dioIn();
    turnaround();
    uint8_t ack = (uint8_t)readBits(3);

    if (ack == SWD_WAIT) {
      // Hand the bus back and retry.
      turnaround();
      dioOut();
      digitalWrite(_pinSwdio, LOW);
      continue;
    }
    if (ack != SWD_OK) {
      // FAULT or no-ack: give the bus back and report.
      turnaround();
      dioOut();
      digitalWrite(_pinSwdio, LOW);
      return ack == 0 ? SWD_NOACK : ack;
    }

    if (isRead) {
      uint32_t value = readBits(32);
      uint8_t par = (uint8_t)readBits(1);
      turnaround();  // target -> host
      dioOut();
      digitalWrite(_pinSwdio, LOW);
      if (par != parity32(value)) return SWD_PARITY;
      data = value;
      return SWD_OK;
    } else {
      turnaround();  // target -> host (ACK read done, now host drives data)
      dioOut();
      writeBits(data, 32);
      writeBit(parity32(data));
      digitalWrite(_pinSwdio, LOW);
      return SWD_OK;
    }
  }
  return SWD_WAIT;
}

bool Swd::readDP(uint8_t addr, uint32_t &out) {
  uint8_t ack = transfer(false, true, addr, out);
  if (ack != SWD_OK) { _lastError = "DP read failed"; return false; }
  return true;
}

bool Swd::writeDP(uint8_t addr, uint32_t val) {
  uint32_t d = val;
  uint8_t ack = transfer(false, false, addr, d);
  if (ack != SWD_OK) { _lastError = "DP write failed"; return false; }
  return true;
}

bool Swd::readAP(uint8_t addr, uint32_t &out) {
  // AP reads are pipelined: the AP access returns the PREVIOUS result, so the
  // real value comes from RDBUFF.
  uint32_t dummy;
  if (transfer(true, true, addr, dummy) != SWD_OK) { _lastError = "AP read failed"; return false; }
  return readDP(DP_RDBUFF, out);
}

bool Swd::writeAP(uint8_t addr, uint32_t val) {
  uint32_t d = val;
  uint8_t ack = transfer(true, false, addr, d);
  if (ack != SWD_OK) { _lastError = "AP write failed"; return false; }
  return true;
}

bool Swd::select(uint32_t value) {
  if (value == _select) return true;
  if (!writeDP(DP_SELECT, value)) return false;
  _select = value;
  return true;
}

bool Swd::setCsw(uint32_t sizeField) {
  uint32_t csw = CSW_BASE | (1 << 4) | sizeField;  // AddrInc=single
  if (csw == _csw) return true;
  if (!select(0)) return false;
  if (!writeAP(AP_CSW, csw)) return false;
  _csw = csw;
  return true;
}

bool Swd::setTar(uint32_t addr) {
  if (!select(0)) return false;
  return writeAP(AP_TAR, addr);
}

bool Swd::connect(uint32_t &idcodeOut) {
  _csw = 0xFFFFFFFF;
  _select = 0xFFFFFFFF;

  // 1) reset, 2) JTAG->SWD switch (0xE79E), 3) reset, 4) idle.
  lineReset();
  writeBits(0xE79E, 16);
  lineReset();
  idleCycles(4);

  // DPIDR must be the first read after a reset.
  if (!readDP(DP_IDCODE, idcodeOut)) { _lastError = "no SWD IDCODE (check wiring/power)"; return false; }
  if (idcodeOut == 0 || idcodeOut == 0xFFFFFFFF) { _lastError = "invalid SWD IDCODE"; return false; }

  // Clear sticky errors, then power up the debug domain.
  writeDP(DP_ABORT, 0x1E);  // STKCMPCLR|STKERRCLR|WDERRCLR|ORUNERRCLR
  if (!select(0)) return false;
  if (!writeDP(DP_CTRLSTAT, 0x50000000)) return false;  // CSYSPWRUPREQ|CDBGPWRUPREQ
  for (int i = 0; i < 100; i++) {
    uint32_t stat;
    if (!readDP(DP_CTRLSTAT, stat)) return false;
    if ((stat & 0xA0000000) == 0xA0000000) break;  // both ACKs
    delay(1);
    if (i == 99) { _lastError = "debug power-up timeout"; return false; }
  }
  _csw = 0xFFFFFFFF;  // force CSW re-write on first access
  return true;
}

void Swd::release() {
  dioIn();
  pinMode(_pinSwclk, INPUT);
}

void Swd::driveNrst(int level) {
  if (_pinNrst < 0) return;
  if (level == 0) {
    pinMode(_pinNrst, OUTPUT);
    digitalWrite(_pinNrst, LOW);  // assert
  } else {
    pinMode(_pinNrst, INPUT);  // release (open-drain: let the net pull high)
  }
}

bool Swd::readWord(uint32_t addr, uint32_t &valueOut) {
  if (!setCsw(CSW_SIZE_WORD)) return false;
  if (!setTar(addr)) return false;
  return readAP(AP_DRW, valueOut);
}

bool Swd::writeWord(uint32_t addr, uint32_t value) {
  if (!setCsw(CSW_SIZE_WORD)) return false;
  if (!setTar(addr)) return false;
  if (!writeAP(AP_DRW, value)) return false;
  // Flush: a DP read ensures the AP write has retired before we return.
  uint32_t flush;
  return readDP(DP_RDBUFF, flush);
}

bool Swd::writeHalf(uint32_t addr, uint16_t value) {
  if (!setCsw(CSW_SIZE_HALF)) return false;
  if (!setTar(addr)) return false;
  // Place the halfword on the correct byte lane for its address.
  uint32_t lane = (uint32_t)value << (8 * (addr & 2));
  if (!writeAP(AP_DRW, lane)) return false;
  uint32_t flush;
  return readDP(DP_RDBUFF, flush);
}

bool Swd::readBlock(uint32_t addr, uint8_t *dst, uint32_t byteLen) {
  if (!setCsw(CSW_SIZE_WORD)) return false;
  uint32_t remaining = byteLen / 4;
  uint32_t outIdx = 0;
  while (remaining) {
    // The MEM-AP auto-increment wraps at a 1 KB (0x400) boundary, so re-arm TAR
    // at each page.
    uint32_t pageWords = (0x400 - (addr & 0x3FF)) / 4;
    uint32_t run = remaining < pageWords ? remaining : pageWords;
    if (!setTar(addr)) return false;
    // Prime the pipeline: this AP read starts word0 and returns stale data.
    uint32_t discard;
    if (transfer(true, true, AP_DRW, discard) != SWD_OK) { _lastError = "block read failed"; return false; }
    for (uint32_t i = 0; i < run; i++) {
      uint32_t w;
      if (i < run - 1) {
        if (transfer(true, true, AP_DRW, w) != SWD_OK) { _lastError = "block read failed"; return false; }
      } else {
        if (!readDP(DP_RDBUFF, w)) return false;  // flush the final word
      }
      dst[outIdx++] = w & 0xFF;
      dst[outIdx++] = (w >> 8) & 0xFF;
      dst[outIdx++] = (w >> 16) & 0xFF;
      dst[outIdx++] = (w >> 24) & 0xFF;
    }
    addr += run * 4;
    remaining -= run;
  }
  return true;
}
