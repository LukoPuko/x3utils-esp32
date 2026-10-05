#include "board.h"

#include "config.h"

X3Board x3board;

#if defined(X3_BOARD_TUNER)
static const bool kHasLed = true;
#else
// Dev boards: GPIO48 on an S3 DevKit is an addressable RGB LED, so only drive
// the LED on our own PCB.
static const bool kHasLed = false;
#endif

// Both sense dividers are 100k/100k, i.e. the pin sees half the voltage.
static int readDivided(int pin) {
  if (pin < 0) return -1;
  uint32_t sum = 0;
  for (int i = 0; i < 8; i++) sum += analogReadMilliVolts(pin);
  return (int)(sum / 8) * 2;
}

void X3Board::begin() {
  if (PIN_TGT_EN >= 0) {
    digitalWrite(PIN_TGT_EN, LOW);
    pinMode(PIN_TGT_EN, OUTPUT);
  }
  if (PIN_VTGT_SENSE >= 0) analogSetPinAttenuation(PIN_VTGT_SENSE, ADC_11db);
  if (PIN_VBAT_SENSE >= 0) analogSetPinAttenuation(PIN_VBAT_SENSE, ADC_11db);
  if (PIN_VBUS_SENSE >= 0) analogSetPinAttenuation(PIN_VBUS_SENSE, ADC_11db);
  if (kHasLed && PIN_LED_DEFAULT >= 0) {
    pinMode(PIN_LED_DEFAULT, OUTPUT);
    digitalWrite(PIN_LED_DEFAULT, LOW);
  }
}

void X3Board::loopTick(bool busy) {
  if (!kHasLed || PIN_LED_DEFAULT < 0) return;
  uint32_t now = millis();
  // busy: 100 ms on / 100 ms off; idle: 40 ms flash every 2 s
  uint32_t period = busy ? 200 : 2000;
  uint32_t onTime = busy ? 100 : 40;
  bool on = (now - _ledT) % period < onTime;
  if (on != _ledOn) {
    _ledOn = on;
    digitalWrite(PIN_LED_DEFAULT, on ? HIGH : LOW);
  }
}

bool X3Board::hasTargetPower() const { return PIN_TGT_EN >= 0; }

bool X3Board::setTargetPower(bool on, String &why, bool skipExternalCheck) {
  if (!hasTargetPower()) { why = "This board has no switchable target supply."; return false; }
  if (on && !_tgtOn && !skipExternalCheck) {
    int mv = targetMillivolts();
    if (mv > TARGET_EXTERNAL_MV) {
      why = String("VCU already shows ") + mv + " mV — it is powered from another source. "
            "Not switching the tool's supply on.";
      return false;
    }
  }
  digitalWrite(PIN_TGT_EN, on ? HIGH : LOW);
  _tgtOn = on;
  return true;
}

bool X3Board::dischargeTarget(uint32_t timeoutMs) {
  if (!hasTargetPower()) return false;
  digitalWrite(PIN_TGT_EN, LOW);
  _tgtOn = false;
  uint32_t start = millis();
  while (millis() - start < timeoutMs) {
    int mv = targetMillivolts();
    if (mv >= 0 && mv < 300) return true;
    delay(20);
  }
  return false;
}

int X3Board::targetMillivolts() const { return readDivided(PIN_VTGT_SENSE); }
int X3Board::batteryMillivolts() const { return readDivided(PIN_VBAT_SENSE); }

int X3Board::batteryPercent() const {
  int mv = batteryMillivolts();
  if (mv < 0) return -1;
  // Coarse open-circuit curve of a 1S LiPo (good enough for a gauge).
  static const int kMv[] = {3300, 3500, 3600, 3700, 3750, 3800, 3900, 4000, 4100, 4200};
  static const int kPct[] = {0, 5, 10, 25, 40, 50, 65, 80, 92, 100};
  if (mv <= kMv[0]) return 0;
  for (int i = 1; i < 10; i++) {
    if (mv <= kMv[i]) return kPct[i - 1] + (kPct[i] - kPct[i - 1]) * (mv - kMv[i - 1]) / (kMv[i] - kMv[i - 1]);
  }
  return 100;
}

// Read through the ADC: a 5 V VBUS halves to ~2.5 V, right at the S3's
// digital VIH threshold, so a digitalRead() would be unreliable.
bool X3Board::usbPresent() const { return readDivided(PIN_VBUS_SENSE) > 3500; }
