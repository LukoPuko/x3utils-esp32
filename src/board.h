// Board support for the X3-Tuner PCB (see hardware/): battery and USB sensing,
// the GPIO-switched 3.3 V supply for the target VCU, and the status LED.
//
// On plain dev boards every feature reports "not present" (pins are -1 in
// config.h) and the firmware behaves exactly as before.

#pragma once

#include <Arduino.h>

class X3Board {
 public:
  void begin();

  // Status LED: slow heartbeat when idle, fast blink while an op runs.
  void loopTick(bool busy);

  bool hasTargetPower() const;
  bool targetPowered() const { return _tgtOn; }

  // Switch the 3.3 V target supply. Turning it on is refused (with [why])
  // while the VCU already carries a voltage from another source, so two
  // supplies never fight. [skipExternalCheck] is only for callers that have
  // just discharged the rail themselves (residual charge is not a source).
  bool setTargetPower(bool on, String &why, bool skipExternalCheck = false);

  // Turn the supply off and wait (up to [timeoutMs]) until the VCU's 3V3 rail
  // has discharged — used before an automatic power-race.
  bool dischargeTarget(uint32_t timeoutMs);

  int targetMillivolts() const;  // -1 if not measurable
  int batteryMillivolts() const; // -1 if not measurable
  int batteryPercent() const;    // -1 if unknown
  bool usbPresent() const;       // false if unknown

 private:
  bool _tgtOn = false;
  uint32_t _ledT = 0;
  bool _ledOn = false;
};

extern X3Board x3board;
