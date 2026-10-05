"""Generate the KiCad 7 schematic (and the project symbol library) from circuit.py.

Every pin gets a short wire stub and a net label (or a no-connect flag), so the
schematic is guaranteed to carry exactly the netlist the PCB was built from.
"""

import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
from sexpr import Q, dump, find, find_all, parse  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.normpath(os.path.join(HERE, "..", "kicad"))
SYMROOT = "/usr/share/kicad/symbols"
SCH = os.path.join(KDIR, C.PROJECT + ".kicad_sch")
LIB = os.path.join(KDIR, C.PROJECT + ".kicad_sym")
ROOT_UUID = str(uuid.uuid5(uuid.NAMESPACE_URL, "x3tuner/root-sheet"))
GRID = 1.27
STUB = 2.54


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "x3tuner/" + "/".join(map(str, parts))))


def sym_uuid(ref):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "x3tuner/" + ref))


def snap(v):
    return round(round(v / GRID) * GRID, 4)


# ── project symbol library (parts KiCad's stock library lacks) ───────────────
def ic_symbol(name, ref, fp, desc, left, right, width=12.7, datasheet=""):
    """Rectangular IC symbol. left/right: [(number, name, type), ...] top→down."""
    rows = max(len(left), len(right))
    h = (rows + 1) * 2.54
    top = snap(h / 2)
    hw = width / 2
    pins = []
    for side, plist in ((-1, left), (1, right)):
        for i, (num, pname, ptype) in enumerate(plist):
            y = top - 2.54 * (i + 1)
            x = side * (hw + 2.54)
            ang = 0 if side < 0 else 180
            pins.append(
                '      (pin %s line (at %s %s %d) (length 2.54)\n'
                '        (name "%s" (effects (font (size 1.27 1.27))))\n'
                '        (number "%s" (effects (font (size 1.27 1.27))))\n      )\n'
                % (ptype, _n(x), _n(y), ang, pname, num))
    return (
        '  (symbol "%s" (in_bom yes) (on_board yes)\n'
        '    (property "Reference" "%s" (at 0 %s 0) (effects (font (size 1.27 1.27))))\n'
        '    (property "Value" "%s" (at 0 %s 0) (effects (font (size 1.27 1.27))))\n'
        '    (property "Footprint" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '    (property "Datasheet" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '    (property "ki_description" "%s" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))\n'
        '    (symbol "%s_0_1"\n'
        '      (rectangle (start %s %s) (end %s %s) (stroke (width 0.254) (type default)) (fill (type background)))\n'
        '    )\n'
        '    (symbol "%s_1_1"\n%s    )\n  )\n'
        % (name, ref, _n(top + 1.27), name, _n(-top - 1.27), fp, datasheet, desc,
           name, _n(-hw), _n(top), _n(hw), _n(-top), name, "".join(pins)))


def _n(v):
    s = ("%.4f" % v).rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def write_project_lib():
    syms = [
        ic_symbol("TP4056", "U", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm",
                  "1A Li-Ion linear charger (ESOP-8)",
                  [("4", "VCC", "power_in"), ("8", "CE", "input"), ("1", "TEMP", "input"),
                   ("2", "PROG", "passive")],
                  [("5", "BAT", "power_out"), ("7", "~{CHRG}", "open_collector"),
                   ("6", "~{STDBY}", "open_collector"), ("3", "GND", "power_in"),
                   ("9", "EP", "passive")],
                  datasheet="https://www.lcsc.com/datasheet/lcsc_datasheet_1809261820_TOPPOWER-Nanjing-Extension-Microelectronics-TP4056-42-ESOP8_C16581.pdf"),
        ic_symbol("DW01A", "U", "Package_TO_SOT_SMD:SOT-23-6",
                  "1S Li-Ion battery protection IC",
                  [("5", "VCC", "power_in"), ("2", "CS", "input"), ("4", "TD", "input"),
                   ("6", "GND", "power_in")],
                  [("1", "OD", "output"), ("3", "OC", "output")], width=10.16),
        ic_symbol("8205_SOT-23-6", "Q", "Package_TO_SOT_SMD:SOT-23-6",
                  "Dual N-MOSFET, common drain, 1S battery protection (FS8205/HJ8205)",
                  [("1", "S1", "passive"), ("6", "G1", "input"), ("2", "D", "passive")],
                  [("3", "S2", "passive"), ("4", "G2", "input"), ("5", "D", "passive")],
                  width=10.16),
    ]
    with open(LIB, "w") as f:
        f.write("(kicad_symbol_lib (version 20220914) (generator x3tuner_gen)\n")
        f.write("".join(syms))
        f.write(")\n")
    with open(os.path.join(KDIR, "sym-lib-table"), "w") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "%s")(type "KiCad")'
                '(uri "${KIPRJMOD}/%s.kicad_sym")(options "")(descr "X3-Tuner project symbols"))\n)\n'
                % (C.PROJECT, C.PROJECT))


# ── symbol loading / flattening ──────────────────────────────────────────────
_libcache = {}


def _lib(name):
    if name not in _libcache:
        path = LIB if name == C.PROJECT else os.path.join(SYMROOT, name + ".kicad_sym")
        _libcache[name] = {str(s[1]): s for s in find_all(parse(open(path).read())[0], "symbol")}
    return _libcache[name]


def load_symbol(lib_id):
    """Return a flattened copy of the library symbol, renamed to lib_id."""
    lib, name = lib_id.split(":")
    syms = _lib(lib)
    s = syms[name]
    ext = find(s, "extends")
    if ext:
        parent = load_symbol(lib + ":" + str(ext[1]))
        pname = lib_id_base(str(ext[1]))
        flat = [x for x in parent if not (isinstance(x, list) and x[0] in ("property",))]
        flat[1] = Q(lib_id)
        props = {str(p[1]): p for p in find_all(parent, "property")}
        for p in find_all(s, "property"):
            props[str(p[1])] = p
        out = flat[:2]
        for x in flat[2:]:
            if isinstance(x, list) and x[0] == "symbol":
                x = list(x)
                x[1] = Q(re.sub("^" + re.escape(pname), name, str(x[1])))
            out.append(x)
        # properties must come before the unit sub-symbols
        idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == "symbol")
        out[idx:idx] = list(props.values())
        return out
    s = list(s)
    s[1] = Q(lib_id)
    return s


def lib_id_base(name):
    return name


def symbol_pins(sym):
    pins = []
    for unit in find_all(sym, "symbol"):
        for p in find_all(unit, "pin"):
            at = find(p, "at")
            num = str(find(p, "number")[1])
            hidden = "hide" in p
            pins.append((num, float(at[1]), float(at[2]), int(float(at[3])) if len(at) > 3 else 0, hidden))
    return pins


# ── schematic writer ─────────────────────────────────────────────────────────
OUT_DIR = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}   # stub direction (sch)
LABEL_ANG = {(-1, 0): 180, (1, 0): 0, (0, -1): 90, (0, 1): 270}


class Sheet:
    def __init__(self):
        self.items = []
        self.lib_symbols = {}

    def wire(self, a, b):
        self.items.append(
            "  (wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))\n"
            % (_n(a[0]), _n(a[1]), _n(b[0]), _n(b[1]), uid("w", a, b)))

    def label(self, net, at, d):
        ang = LABEL_ANG[d]
        just = "left bottom" if ang in (0, 90) else "right bottom"
        self.items.append(
            '  (label "%s" (at %s %s %d) (fields_autoplaced)\n'
            '    (effects (font (size 1.27 1.27)) (justify %s)) (uuid %s))\n'
            % (net, _n(at[0]), _n(at[1]), ang, just, uid("l", net, at)))

    def no_connect(self, at):
        self.items.append("  (no_connect (at %s %s) (uuid %s))\n" % (_n(at[0]), _n(at[1]), uid("nc", at)))

    def text(self, x, y, size, s, bold=False):
        self.items.append(
            '  (text "%s" (at %s %s 0)\n    (effects (font (size %s %s)%s) (justify left bottom)) (uuid %s))\n'
            % (s.replace('"', "'"), _n(x), _n(y), _n(size), _n(size), " bold" if bold else "", uid("t", x, y)))

    def symbol(self, ref, lib_id, value, x, y, props, pin_nets, in_bom=True):
        sym = load_symbol(lib_id)
        self.lib_symbols[lib_id] = sym
        x, y = snap(x), snap(y)
        lines = ['  (symbol (lib_id "%s") (at %s %s 0) (unit 1)\n'
                 '    (in_bom %s) (on_board yes) (dnp no)\n    (uuid %s)\n'
                 % (lib_id, _n(x), _n(y), "yes" if in_bom else "no", sym_uuid(ref))]
        libprops = {str(p[1]): p for p in find_all(sym, "property")}
        allprops = [("Reference", ref), ("Value", value)] + props
        for i, (k, v) in enumerate(allprops):
            lp = libprops.get(k)
            ang = 0
            if lp is not None and k in ("Reference", "Value"):
                at = find(lp, "at")
                px, py = x + float(at[1]), y - float(at[2])
                ang = int(float(at[3])) if len(at) > 3 else 0
                eff = find(lp, "effects")
                just = find(eff, "justify") if eff else None
                js = " (justify %s)" % " ".join(str(j) for j in just[1:]) if just else ""
                hide = ""
            else:
                px, py, js, hide = x, y, "", " hide"
            lines.append('    (property "%s" "%s" (at %s %s %d)\n      (effects (font (size 1.27 1.27))%s%s))\n'
                         % (k, v, _n(px), _n(py), ang, js, hide))
        pins = symbol_pins(sym)
        for num, *_ in pins:
            lines.append('    (pin "%s" (uuid %s))\n' % (num, uid("pin", ref, num)))
        lines.append('    (instances\n      (project "%s"\n        (path "/%s" (reference "%s") (unit 1))\n      )\n    )\n  )\n'
                     % (C.PROJECT, ROOT_UUID, ref))
        self.items.append("".join(lines))

        # Wires + labels per pin location (stacked pins share one stub).
        seen = {}
        for num, px, py, ang, hidden in pins:
            pos = (snap(x + px), snap(y - py))
            net = pin_nets.get(num)
            if pos in seen:
                if seen[pos] != net:
                    raise SystemExit("%s: stacked pins with different nets at %s" % (ref, pos))
                continue
            seen[pos] = net
            if net is None:
                self.no_connect(pos)
                continue
            d = OUT_DIR[ang % 360]
            end = (snap(pos[0] + d[0] * STUB), snap(pos[1] + d[1] * STUB))
            self.wire(pos, end)
            self.label(net, end, d)
        return pins

    def write(self, path):
        hdr = ('(kicad_sch (version 20230121) (generator eeschema)\n\n  (uuid %s)\n\n  (paper "A3")\n\n'
               '  (title_block\n    (title "%s")\n    (date "2026-10-05")\n    (rev "%s")\n'
               '    (company "x3utils-esp32")\n'
               '    (comment 1 "Generiert aus hardware/gen/circuit.py - nicht von Hand editieren, sondern circuit.py aendern")\n'
               '    (comment 2 "ESP32-S3 SWD-Programmer fuer AT32F415 VCUs der X3-Scooter-Familie")\n  )\n\n'
               % (ROOT_UUID, C.TITLE, C.REV))
        libs = "  (lib_symbols\n" + "".join(
            "    " + dump(s, 2) + "\n" for _, s in sorted(self.lib_symbols.items())) + "  )\n\n"
        body = "".join(self.items)
        tail = '\n  (sheet_instances\n    (path "/" (page "1"))\n  )\n)\n'
        with open(path, "w") as f:
            f.write(hdr + libs + body + tail)


def main():
    write_project_lib()
    _libcache.pop(C.PROJECT, None)
    sh = Sheet()
    for p in C.PARTS:
        props = [("Footprint", p.fp), ("Datasheet", "")]
        if p.lcsc:
            props.append(("LCSC", p.lcsc))
        if p.mfr:
            props.append(("Hersteller", p.mfr))
        if p.desc:
            props.append(("Beschreibung", p.desc))
        pins = sh.symbol(p.ref, p.sym, p.value, p.sch[0], p.sch[1], props, p.pins, in_bom=p.bom)
        missing = {n for n, *_ in pins} ^ set(p.pins)
        if missing:
            raise SystemExit("%s: pin mismatch symbol vs circuit: %s" % (p.ref, sorted(missing)))

    # Power flags (ERC: nets fed only through passive pins)
    for i, net in enumerate(C.PWR_FLAG_NETS):
        x, y = 340 + (i % 3) * 22, 215 + (i // 3) * 18
        n = "#FLG%02d" % (i + 1)
        sh.lib_symbols["power:PWR_FLAG"] = load_symbol("power:PWR_FLAG")
        sh.symbol(n, "power:PWR_FLAG", "PWR_FLAG", x, y, [("Footprint", ""), ("Datasheet", "")],
                  {"1": net}, in_bom=False)

    for x, y, size, s in C.SCH_TEXT:
        sh.text(x, y, size, s, bold=True)
    for i, s in enumerate(C.NOTES):
        sh.text(335, 150 + i * 5, 1.5, s)
    sh.write(SCH)
    print("schematic ->", SCH)


if __name__ == "__main__":
    main()
