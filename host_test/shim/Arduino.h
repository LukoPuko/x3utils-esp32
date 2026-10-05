// Minimal Arduino shim for host-side unit testing of portable logic.
#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>

#include <cstdlib>

#define PROGMEM
#define F(x) x

// GPIO / timing constants and stubs so the embedded cores compile on host.
#define INPUT 0x01
#define OUTPUT 0x03
#define INPUT_PULLUP 0x05
#define HIGH 0x1
#define LOW 0x0
#define HEX 16
#define DEC 10
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int digitalRead(int) { return 0; }
inline void delay(unsigned long) {}
inline void delayMicroseconds(unsigned int) {}
inline unsigned long millis() { static unsigned long t = 0; return t += 1000000; }
inline unsigned long micros() { return millis() * 1000; }
inline void *ps_malloc(size_t n) { return malloc(n); }

class String {
 public:
  String() {}
  String(const char *s) : _s(s ? s : "") {}
  String(const std::string &s) : _s(s) {}
  String(char c) { _s = std::string(1, c); }
  String(int v) { char b[16]; snprintf(b, sizeof b, "%d", v); _s = b; }
  String(unsigned v) { char b[16]; snprintf(b, sizeof b, "%u", v); _s = b; }
  String(long v) { char b[24]; snprintf(b, sizeof b, "%ld", v); _s = b; }
  String(unsigned long v) { char b[24]; snprintf(b, sizeof b, "%lu", v); _s = b; }
  String(unsigned v, int base) { char b[24]; snprintf(b, sizeof b, base == 16 ? "%x" : "%u", v); _s = b; }
  String(unsigned long v, int base) { char b[24]; snprintf(b, sizeof b, base == 16 ? "%lx" : "%lu", v); _s = b; }
  String(int v, int base) { char b[24]; snprintf(b, sizeof b, base == 16 ? "%x" : "%d", (unsigned)v); _s = b; }

  size_t length() const { return _s.size(); }
  const char *c_str() const { return _s.c_str(); }
  char operator[](size_t i) const { return i < _s.size() ? _s[i] : '\0'; }

  bool startsWith(const String &p) const { return _s.rfind(p._s, 0) == 0; }
  String substring(size_t a) const { return a <= _s.size() ? String(_s.substr(a)) : String(); }
  String substring(size_t a, size_t b) const {
    if (a > _s.size()) return String();
    if (b > _s.size()) b = _s.size();
    if (b < a) b = a;
    return String(_s.substr(a, b - a));
  }
  int indexOf(char c) const { auto p = _s.find(c); return p == std::string::npos ? -1 : (int)p; }
  int indexOf(char c, int start) const { auto p = _s.find(c, start); return p == std::string::npos ? -1 : (int)p; }
  void toLowerCase() { for (auto &c : _s) c = tolower((unsigned char)c); }
  void toUpperCase() { for (auto &c : _s) c = toupper((unsigned char)c); }

  String operator+(const String &o) const { return String(_s + o._s); }
  String operator+(const char *o) const { return String(_s + std::string(o)); }
  String &operator+=(const String &o) { _s += o._s; return *this; }
  bool operator==(const String &o) const { return _s == o._s; }
  bool operator==(const char *o) const { return _s == std::string(o); }
  bool operator!=(const String &o) const { return !(*this == o); }
  bool operator!=(const char *o) const { return !(*this == o); }

  std::string _s;
};

inline String operator+(const char *a, const String &b) { return String(std::string(a) + b._s); }
