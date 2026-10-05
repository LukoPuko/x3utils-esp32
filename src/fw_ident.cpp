#include "fw_ident.h"

namespace fwident {

const uint8_t kCompatSignature[16] = {0xFE, 0x80, 0x1C, 0xB2, 0xD1, 0xEF, 0x41, 0xA6,
                                      0xA4, 0x17, 0x31, 0xF5, 0xA0, 0x68, 0x24, 0xF0};

static const uint32_t RAND_LEN = 6;  // device rand bytes following the key

// ── version matrix (subset mirrors fw_version.dart) ──────────────────────────
struct VerList {
  const char *key;  // "<model>/<TYPE>"
  const char *versions;
};
// KNOWN: every version we can name.
static const VerList kKnown[] = {
    {"zt3/VCU", "1.4.3 1.4.5 1.4.8 1.4.10 1.4.11 1.4.14 1.4.15 1.5.2 1.5.3 1.5.5 1.5.7 1.5.8 1.5.9"},
    {"zt3/MCU", "1.2.4 1.2.8 1.2.11 1.4.3 1.5.2"},
    {"g3/VCU", "1.4.8 1.5.4 1.5.5 1.5.6 1.5.8 1.5.13 1.5.15 1.6.1 1.6.2 1.6.3 1.6.4"},
    {"g3/MCU", "1.3.15 1.4.8 1.4.12 1.5.0 1.5.7"},
    {"f3/VCU", "1.5.4 1.5.5 1.5.6 1.5.8 1.5.13 1.6.0 1.6.1 1.6.2"},
    {"f3/MCU", "1.4.1 1.4.5 1.4.12 1.5.0"},
    {"gt3/VCU", "1.5.8"},
    {"gt3/MCU", "1.8.4"},
};
// BLACKLIST: the floor at/above which SHU compat refuses.
static const VerList kBlacklist[] = {
    {"zt3/VCU", "1.5.9"}, {"zt3/MCU", "1.6.0"}, {"g3/VCU", "1.6.3"},
    {"g3/MCU", "1.6.0"},  {"f3/VCU", "1.6.3"},  {"f3/MCU", "1.6.0"},
};

static int verValue(int a, int b, int c) { return (a << 8) | (b << 4) | c; }

static bool parseVer(const String &s, int &outValue, String &outText) {
  int a, b, c;
  if (sscanf(s.c_str(), "%d.%d.%d", &a, &b, &c) != 3) return false;
  if (a > 15 || b > 15 || c > 15) return false;
  outValue = verValue(a, b, c);
  outText = String(a) + "." + String(b) + "." + String(c);
  return true;
}

static String matrixKey(const String &model, const String &type) {
  String m = model;
  m.toLowerCase();
  String t = type;
  t.toUpperCase();
  return m + "/" + t;
}

static void collectVersions(const VerList *table, size_t n, const String &key,
                            std::vector<int> &values, std::vector<String> &texts) {
  for (size_t i = 0; i < n; i++) {
    if (key != table[i].key) continue;
    String list = table[i].versions;
    int start = 0;
    while (start < (int)list.length()) {
      int sp = list.indexOf(' ', start);
      String tok = sp < 0 ? list.substring(start) : list.substring(start, sp);
      int v;
      String txt;
      if (parseVer(tok, v, txt)) { values.push_back(v); texts.push_back(txt); }
      if (sp < 0) break;
      start = sp + 1;
    }
  }
}

// ── Thumb-2 immediate decoder (MOVW + MOV.W ThumbExpandImm) ───────────────────
static uint32_t thumbExpandImm(uint32_t imm12) {
  if ((imm12 & 0xC00) == 0) {
    uint32_t v = imm12 & 0xFF;
    switch ((imm12 >> 8) & 3) {
      case 0: return v;
      case 1: return (v << 16) | v;
      case 2: return (v << 24) | (v << 8);
      default: return (v << 24) | (v << 16) | (v << 8) | v;
    }
  }
  uint32_t unrotated = 0x80 | (imm12 & 0x7F);
  uint32_t rot = (imm12 >> 7) & 0x1F;
  return ((unrotated >> rot) | (unrotated << (32 - rot))) & 0xFFFFFFFF;
}

static bool immediateAt(const uint8_t *b, uint32_t i, uint32_t &out) {
  uint32_t hw1 = b[i] | (b[i + 1] << 8);
  uint32_t hw2 = b[i + 2] | (b[i + 3] << 8);
  if (hw2 & 0x8000) return false;  // not a 32-bit Thumb-2 second halfword
  if ((hw1 & 0xFBF0) == 0xF240) {  // MOVW Rd,#imm16
    out = ((hw1 & 0xF) << 12) | (((hw1 >> 10) & 1) << 11) | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xFF);
    return true;
  }
  if ((hw1 & 0xFBEF) == 0xF04F) {  // MOV.W Rd,#const
    out = thumbExpandImm((((hw1 >> 10) & 1) << 11) | (((hw2 >> 12) & 7) << 8) | (hw2 & 0xFF));
    return true;
  }
  return false;
}

// Returns distinct matched version values present in [payload].
static std::vector<int> scanVersions(const uint8_t *payload, uint32_t len,
                                     const std::vector<int> &wanted) {
  std::vector<int> hits;
  if (wanted.empty() || len < 4) return hits;
  for (uint32_t i = 0; i + 3 < len; i += 2) {
    uint32_t v;
    if (!immediateAt(payload, i, v)) continue;
    for (int w : wanted) {
      if ((int)v == w) {
        bool seen = false;
        for (int h : hits) if (h == w) seen = true;
        if (!seen) hits.push_back(w);
      }
    }
  }
  return hits;
}

// ── banner ───────────────────────────────────────────────────────────────────
struct Banner {
  bool valid = false;
  bool supported = false;
  String type;   // VCU/MCU
  String model;  // for VCU only
  String raw;
};

static String modelFromVcuCode(const String &code) {
  if (code == "xxU2") return "zt3";
  if (code == "xxG3") return "g3";
  if (code == "xGT3") return "gt3";
  if (code == "xxF3") return "f3";
  return "";
}

static Banner bannerAt(const uint8_t *b, size_t len, uint32_t off) {
  Banner out;
  if (len < off + 16) return out;
  String s;
  for (uint32_t i = 0; i < 16; i++) s += (char)b[off + i];
  // Match ^SCOOTER_(VCU|MCU)_(....)$
  if (!s.startsWith("SCOOTER_")) return out;
  String rest = s.substring(8);
  if (rest.length() != 8) return out;
  String type = rest.substring(0, 3);
  if (rest[3] != '_') return out;
  String code = rest.substring(4);
  if (type != "VCU" && type != "MCU") return out;
  out.valid = true;
  out.raw = s;
  out.type = type;
  if (type == "MCU") {
    out.supported = (code == "0001");
  } else {
    out.model = modelFromVcuCode(code);
    out.supported = out.model.length() > 0;
  }
  return out;
}

// ── compat key/rand/xtea classification ──────────────────────────────────────
static bool regionIsSignature(const uint8_t *img, size_t len) {
  if (len < COMPAT_OFFSET + 16) return false;
  for (int i = 0; i < 16; i++) if (img[COMPAT_OFFSET + i] != kCompatSignature[i]) return false;
  return true;
}
static bool regionAllFf(const uint8_t *img, size_t len, uint32_t at, uint32_t n) {
  if (len < at + n) return false;
  for (uint32_t i = 0; i < n; i++) if (img[at + i] != 0xFF) return false;
  return true;
}
static bool asciiAlnum(const uint8_t *img, size_t len, uint32_t at, uint32_t n) {
  if (len < at + n) return false;
  for (uint32_t i = 0; i < n; i++) {
    uint8_t c = img[at + i];
    bool d = c >= 0x30 && c <= 0x39, u = c >= 0x41 && c <= 0x5A, l = c >= 0x61 && c <= 0x7A;
    if (!d && !u && !l) return false;
  }
  return true;
}

enum class FactoryState { factory, alreadyCompatible, cleared, unknown };

static FactoryState factoryState(const uint8_t *img, size_t len) {
  if (regionIsSignature(img, len)) return FactoryState::alreadyCompatible;
  if (regionAllFf(img, len, COMPAT_OFFSET, 16))
    return regionAllFf(img, len, RAND_OFFSET, RAND_LEN) ? FactoryState::cleared : FactoryState::unknown;
  return (asciiAlnum(img, len, COMPAT_OFFSET, 16) && asciiAlnum(img, len, RAND_OFFSET, RAND_LEN))
             ? FactoryState::factory
             : FactoryState::unknown;
}

// XTEA present = 16 ASCII alphanumeric at 0x1440.
static bool xteaPresent(const uint8_t *img, size_t len) {
  return asciiAlnum(img, len, XTEA_OFFSET, 16);
}

bool applyCompatPatch(uint8_t *image, size_t len) {
  if (len < COMPAT_OFFSET + 16) return false;
  for (int i = 0; i < 16; i++) image[COMPAT_OFFSET + i] = kCompatSignature[i];
  for (int i = 0; i < 16; i++) if (image[COMPAT_OFFSET + i] != kCompatSignature[i]) return false;
  return true;
}

std::vector<String> mcuModels() {
  std::vector<String> out;
  for (const auto &row : kKnown) {
    String k = row.key;
    int slash = k.indexOf('/');
    if (slash < 0) continue;
    if (k.substring(slash + 1) == "MCU") out.push_back(k.substring(0, slash));
  }
  return out;
}

static bool modelUnsupported(const String &model) {
  String m = model;
  m.toLowerCase();
  return m == "gt3";
}

String describe(const uint8_t *dump, size_t len) {
  Banner b = bannerAt(dump, len, SLOT_BANNER_OFFSET);
  if (!b.valid) return "no recognised firmware banner";
  if (!b.supported) return String("unsupported banner \"") + b.raw + "\"";
  if (b.type == "MCU") return "MCU firmware (model not carried in banner)";
  return b.model.length() ? (b.model + " VCU firmware") : "VCU firmware";
}

CompatGate evaluateCompat(const uint8_t *dump, size_t len, const String &declaredMcuModel) {
  CompatGate g;
  if (len < SLOT0_REGION_END) { g.message = "Dump too small to identify."; return g; }

  // 1) XTEA present -> too new.
  if (xteaPresent(dump, len)) {
    g.message = "Firmware too new for SHU compat (XTEA present at 0x1440). Nothing written.";
    return g;
  }

  // 2) must be factory state.
  switch (factoryState(dump, len)) {
    case FactoryState::factory: break;
    case FactoryState::alreadyCompatible: g.message = "Already SHU compatible. Nothing written."; return g;
    case FactoryState::cleared: g.message = "Not factory firmware. Nothing written."; return g;
    case FactoryState::unknown: g.message = "Can't confirm factory firmware. Nothing written."; return g;
  }

  // 3) banner / type / model.
  Banner b = bannerAt(dump, len, SLOT_BANNER_OFFSET);
  if (!b.valid || !b.supported) {
    g.message = "Chip is not running firmware x3utils recognises. Nothing written.";
    return g;
  }
  g.banner = b.raw;
  g.type = b.type;
  String model = b.model;
  if (b.type == "MCU") {
    model = declaredMcuModel;
    model.toLowerCase();
    if (model.length() == 0) { g.message = "MCU firmware: pick the scooter model before SHU compat."; return g; }
  }
  g.model = model;

  if (modelUnsupported(model)) {
    g.message = "SHU compat is not supported on " + model + " at any firmware version. Nothing written.";
    return g;
  }

  // 4) version scan over slot 0.
  String key = matrixKey(model, b.type);
  std::vector<int> knownV;
  std::vector<String> knownT, blackT;
  std::vector<int> blackV;
  collectVersions(kKnown, sizeof(kKnown) / sizeof(kKnown[0]), key, knownV, knownT);
  collectVersions(kBlacklist, sizeof(kBlacklist) / sizeof(kBlacklist[0]), key, blackV, blackT);

  std::vector<int> wanted = knownV;
  for (int v : blackV) wanted.push_back(v);

  const uint8_t *payload = dump + SLOT0_OFFSET;
  uint32_t payloadLen = SLOT0_REGION_END - SLOT0_OFFSET;
  std::vector<int> found = scanVersions(payload, payloadLen, wanted);

  // blacklist floor (lowest blacklisted value), applied to the highest match.
  int floor = -1;
  for (int v : blackV) if (floor < 0 || v < floor) floor = v;
  int highest = -1;
  for (int v : found) if (v > highest) highest = v;

  auto verText = [](int v) {
    return String((v >> 8) & 0xF) + "." + String((v >> 4) & 0xF) + "." + String(v & 0xF);
  };

  if (floor >= 0 && highest >= floor) {
    g.version = verText(highest);
    g.message = model + " " + b.type + " " + g.version + " is too new for SHU compat. Nothing written.";
    return g;
  }
  if (found.empty()) {
    g.message = "Firmware version not recognised — SHU compat needs an identified, supported version. Nothing written.";
    return g;
  }
  if (found.size() > 1) {
    g.message = "Firmware version ambiguous — cannot safely SHU-patch. Nothing written.";
    return g;
  }

  g.version = verText(found[0]);
  g.ok = true;
  g.message = model + " " + b.type + " " + g.version;
  return g;
}

}  // namespace fwident
