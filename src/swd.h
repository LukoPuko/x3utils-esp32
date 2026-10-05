// Bit-banged SWD (ARM ADIv5) master for the ESP32.
//
// This is the ESP32's replacement for the ST-LINK. The upstream x3utils engine
// is written against a small debug-probe surface (read/write a debug register,
// read/write memory, drive nRST); this class provides exactly that surface over
// two GPIO pins, so the AT32F415 flash algorithm ported in at32.cpp is the same
// algorithm the desktop/web app runs — only the transport changed.
//
// Derived in spirit from the swdart engine bundled with x3utils (MIT).

#pragma once

#include <Arduino.h>

// ADIv5 acknowledge codes (3-bit, read LSB-first off the wire).
enum SwdAck {
  SWD_OK = 1,
  SWD_WAIT = 2,
  SWD_FAULT = 4,
  SWD_PARITY = 7,  // synthetic: data parity mismatch on a read
  SWD_NOACK = 0,   // synthetic: line never acknowledged
};

class Swd {
 public:
  void configure(int pinSwclk, int pinSwdio, int pinNrst, uint8_t halfClockUs);

  // Full line-reset + JTAG-to-SWD switch + debug-power-up. Returns true and sets
  // [idcodeOut] to the DP IDCODE (DPIDR) on success.
  bool connect(uint32_t &idcodeOut);

  // Release the lines (both inputs) so the target runs on its own.
  void release();

  // nRST / C45 control. level 0 asserts reset (drives low), 1 releases (high-Z
  // via input, matching an open-drain reset net). A board without nRST wired
  // simply ignores these.
  void driveNrst(int level);
  bool hasNrst() const { return _pinNrst >= 0; }

  // ── Memory access through the MEM-AP ───────────────────────────────────────
  // All four return true on success. Debug registers (DHCSR, DEMCR, AIRCR, the
  // AT32 flash controller, …) are just memory to the MEM-AP, so readWord/
  // writeWord cover both "readDebugReg" and ordinary memory in the upstream API.
  bool readWord(uint32_t addr, uint32_t &valueOut);
  bool writeWord(uint32_t addr, uint32_t value);
  bool writeHalf(uint32_t addr, uint16_t value);  // 16-bit, for the FAP rewrite

  // Auto-incrementing block transfers (word granularity) for fast dump/verify.
  bool readBlock(uint32_t addr, uint8_t *dst, uint32_t byteLen);

  const char *lastError() const { return _lastError; }
  uint8_t halfClockUs() const { return _halfClockUs; }
  void setHalfClockUs(uint8_t v) { _halfClockUs = v; }

 private:
  // Line-level helpers.
  inline void delayHalf();
  inline void clockPulse();
  inline void writeBit(uint8_t bit);
  inline uint8_t readBit();
  void writeBits(uint32_t value, uint8_t count);
  uint32_t readBits(uint8_t count);
  void turnaround();
  void dioOut();
  void dioIn();
  void lineReset();
  void idleCycles(uint8_t n);

  // Transaction core. Retries WAIT acks. [isRead] picks direction; [data] is
  // in/out. Returns a SwdAck.
  uint8_t transfer(bool apnDp, bool isRead, uint8_t a23, uint32_t &data);

  bool readDP(uint8_t addr, uint32_t &out);
  bool writeDP(uint8_t addr, uint32_t val);
  bool readAP(uint8_t addr, uint32_t &out);
  bool writeAP(uint8_t addr, uint32_t val);

  bool select(uint32_t value);     // DP SELECT (AP bank)
  bool setCsw(uint32_t sizeField); // MEM-AP CSW size, cached
  bool setTar(uint32_t addr);

  int _pinSwclk = -1;
  int _pinSwdio = -1;
  int _pinNrst = -1;
  uint8_t _halfClockUs = 0;
  bool _dioIsOut = false;

  uint32_t _csw = 0xFFFFFFFF;     // cached CSW, invalid sentinel
  uint32_t _select = 0xFFFFFFFF;  // cached SELECT
  const char *_lastError = "";
};
