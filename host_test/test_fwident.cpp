// Host-side tests for the ported SHU-compat safety gates + Thumb-2 version
// decoder. Builds a synthetic 128 KB AT32F415 image and checks that
// evaluateCompat() reaches the same verdict the desktop/web app would.
#include <cassert>
#include <cstdio>
#include <vector>

#include "fw_ident.h"

static const uint32_t N = 131072;

// Encode a MOVW Rd,#imm16 (32-bit Thumb-2) for the version-constant decoder.
static void putMovw(std::vector<uint8_t> &img, uint32_t off, uint16_t imm) {
  uint32_t i = imm & 0xFFFF;
  uint32_t imm4 = (i >> 12) & 0xF, ibit = (i >> 11) & 1, imm3 = (i >> 8) & 7, imm8 = i & 0xFF;
  uint32_t hw1 = 0xF240 | (ibit << 10) | imm4;       // 1111 0i10 0100 imm4
  uint32_t hw2 = (imm3 << 12) | (0 << 8) | imm8;     // 0 imm3 Rd(0) imm8
  img[off + 0] = hw1 & 0xFF; img[off + 1] = (hw1 >> 8) & 0xFF;
  img[off + 2] = hw2 & 0xFF; img[off + 3] = (hw2 >> 8) & 0xFF;
}

static void setBanner(std::vector<uint8_t> &img, const char *b) {
  memcpy(&img[0x1400], b, 16);  // slot banner at 0x1400 in a full dump
}
static void setAscii(std::vector<uint8_t> &img, uint32_t off, uint32_t n, char c) {
  for (uint32_t i = 0; i < n; i++) img[off + i] = c;
}

// A factory-state G3 VCU image: real banner, ASCII key+rand, no XTEA.
static std::vector<uint8_t> baseG3Vcu() {
  std::vector<uint8_t> img(N, 0x00);
  // plausible vector table so flash looks "present" (not required by gate)
  img[0x1003] = 0x20;
  setBanner(img, "SCOOTER_VCU_xxG3");
  setAscii(img, 0x1420, 16, 'A');  // factory key shape
  setAscii(img, 0x1430, 6, 'B');   // factory rand shape
  for (int i = 0; i < 16; i++) img[0x1440 + i] = 0xFF;  // XTEA cleared
  return img;
}

int main() {
  // 1) Supported G3 VCU 1.5.5 -> OK.
  {
    auto img = baseG3Vcu();
    putMovw(img, 0x4000, 0x155);  // g3 VCU 1.5.5 somewhere in slot 0
    auto g = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[1] ok=%d model=%s type=%s ver=%s msg=%s\n", g.ok, g.model.c_str(), g.type.c_str(), g.version.c_str(), g.message.c_str());
    assert(g.ok);
    assert(g.model == "g3" && g.type == "VCU" && g.version == "1.5.5");
  }

  // 2) Blacklisted G3 VCU 1.6.3 -> refused (too new).
  {
    auto img = baseG3Vcu();
    putMovw(img, 0x4000, 0x163);
    auto g = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[2] ok=%d msg=%s\n", g.ok, g.message.c_str());
    assert(!g.ok);
  }

  // 3) XTEA present -> refused regardless of version.
  {
    auto img = baseG3Vcu();
    putMovw(img, 0x4000, 0x155);
    setAscii(img, 0x1440, 16, 'Z');  // XTEA field present
    auto g = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[3] ok=%d msg=%s\n", g.ok, g.message.c_str());
    assert(!g.ok);
  }

  // 4) Already SHU-compatible (signature present) -> refused.
  {
    auto img = baseG3Vcu();
    putMovw(img, 0x4000, 0x155);
    memcpy(&img[0x1420], fwident::kCompatSignature, 16);
    auto g = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[4] ok=%d msg=%s\n", g.ok, g.message.c_str());
    assert(!g.ok);
  }

  // 5) Unknown version (no known constant) -> refused (unidentified).
  {
    auto img = baseG3Vcu();  // no version constant placed
    auto g = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[5] ok=%d msg=%s\n", g.ok, g.message.c_str());
    assert(!g.ok);
  }

  // 6) MCU banner needs a declared model; supported ZT3 MCU 1.5.2 -> OK.
  {
    std::vector<uint8_t> img(N, 0x00);
    setBanner(img, "SCOOTER_MCU_0001");
    setAscii(img, 0x1420, 16, 'A');
    setAscii(img, 0x1430, 6, 'B');
    for (int i = 0; i < 16; i++) img[0x1440 + i] = 0xFF;
    putMovw(img, 0x5000, 0x152);  // zt3 MCU 1.5.2
    auto noModel = fwident::evaluateCompat(img.data(), img.size(), "");
    printf("[6a] ok=%d msg=%s\n", noModel.ok, noModel.message.c_str());
    assert(!noModel.ok);  // model required
    auto g = fwident::evaluateCompat(img.data(), img.size(), "zt3");
    printf("[6b] ok=%d model=%s type=%s ver=%s\n", g.ok, g.model.c_str(), g.type.c_str(), g.version.c_str());
    assert(g.ok && g.type == "MCU" && g.version == "1.5.2");
  }

  // 7) applyCompatPatch writes exactly the 16-byte signature.
  {
    auto img = baseG3Vcu();
    assert(fwident::applyCompatPatch(img.data(), img.size()));
    assert(memcmp(&img[0x1420], fwident::kCompatSignature, 16) == 0);
  }

  // 8) describe() reports the VCU model.
  {
    auto img = baseG3Vcu();
    String d = fwident::describe(img.data(), img.size());
    printf("[8] describe=%s\n", d.c_str());
    assert(d == "g3 VCU firmware");
  }

  printf("\nALL FWIDENT TESTS PASSED\n");
  return 0;
}
