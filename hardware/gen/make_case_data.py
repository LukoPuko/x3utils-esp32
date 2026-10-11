"""Write <board>/case/board_data.scad from the board's circuit file.

The case model reads every connector / button / LED position from this file,
so moving a part on the PCB moves its cut-out in the case as well. The board
comes from X3_CIRCUIT (see cfg.py); its optional CASE dict names the parts
and holds the case overrides (circuit_carrier.py), without it the X3-Tuner
references apply.

SCAD coordinates: X = board x, Y = BOARD_H - board y (board's port end at
Y = 0, antenna end at Y = BOARD_H), Z = up. Units mm.

usage: make_case_data.py            write board_data.scad
       make_case_data.py --paths    print "case_dir name docs_dir title" (make_case.sh)
       make_case_data.py --cams X,Y,Z   print the perspective renders for make_case.sh:
                                        "file part eye_x,eye_y,eye_z,at_x,at_y,at_z"
       make_case_data.py --sheet    print the view-sheet labels (left|right|far end|title)
"""

import os
import sys

try:  # optional: the parts list for the preview renders needs KiCad's pcbnew
    import pcbnew
except ImportError:
    pcbnew = None

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cfg import BASE, DOCS, KDIR, C  # noqa: E402

CASE = getattr(C, "CASE", {})
NAME = CASE.get("name", "x3tuner")
TITLE = CASE.get("title", "X3-Tuner Gehäuse")
CASE_DIR = os.path.join(BASE, "case")
OUT = os.path.join(CASE_DIR, "board_data.scad")
REF = dict(usb="J1", bat="J2", swd="J3", switch="SW1", reset="SW2", boot="SW3",
           led_stat="D4", led_chg=("D2", "D3"))
REF.update(CASE.get("refs", {}))
# Perspective renders: (file, part, eye offset from the look-at point, look-at
# offset from the case centre CASE_CENTER).
CAMS = CASE.get("cameras", [
    ("case-assembly.png", "assembly", (51, -83, 59), (0, 2.575, -2.35)),
    ("case-xray.png", "xray", (51, -83, 59), (0, 2.575, -2.35)),
    ("case-xray-bottom.png", "xray", (-79, -78, -61), (0, 2.575, -2.35)),
    ("case-section.png", "section", (76, 44, 28), (0, 0.575, -1.35)),
    ("case-exploded.png", "exploded", (51, -98, 56), (0, 2.575, 5.65)),
])
# captions of the side views on the dimensioned sheet; a far-end view is added
# when it has a caption
SHEET = CASE.get("sheet", ("Schalter", "USB-C", ""))


def pos(ref):
    p = next(p for p in C.PARTS if p.ref == ref)
    return p.pcb


def Y(y):
    return round(C.BOARD_H - y, 3)


def scad(v):
    if isinstance(v, str):
        return '"%s"' % v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (list, tuple)):
        return "[%s]" % ", ".join(scad(x) for x in v)
    return repr(round(v, 4))


# Body height (mm) and colour of the small parts in the preview renders, by
# footprint name prefix. Connectors, switches and the module have their own
# models in case_core.scad.
BODY = [("R_0402", 0.35, "#1b1b1b"), ("C_0402", 0.5, "#b8946a"), ("C_0603", 0.8, "#b8946a"),
        ("C_0805", 1.0, "#b8946a"), ("LED_", 0.6, None), ("SOT-23", 1.1, "#2b2b2b"),
        ("D_SOD-123", 1.1, "#2b2b2b"), ("SOIC-8", 1.6, "#2b2b2b"), ("TestPoint", 0.05, "#d4af37")]
OWN_MODEL = set(CASE.get("own_model", ("U1", "J1", "J2", "J3", "SW1", "SW2", "SW3")))
LED_COLOR = {"red": "#ff3030", "green": "#30e040", "yellow": "#ffd21a"}


def part_boxes():
    """[x0, y0, w, h, height, colour] per small part, SCAD coordinates."""
    path = os.path.join(KDIR, C.PROJECT + ".kicad_pcb")
    if pcbnew is None or not os.path.exists(path):
        return []
    board = pcbnew.LoadBoard(path)
    edge = board.GetBoardEdgesBoundingBox()
    ox, oy = pcbnew.ToMM(edge.GetLeft()) + 0.05, pcbnew.ToMM(edge.GetTop()) + 0.05
    value = {p.ref: p.value for p in C.PARTS}
    boxes = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        name = fp.GetFPID().GetLibItemName().wx_str()
        body = next((b for b in BODY if name.startswith(b[0])), None)
        if ref in OWN_MODEL or body is None:
            continue
        items = [i for i in fp.GraphicalItems() if i.GetLayer() == pcbnew.F_Fab
                 and not isinstance(i, pcbnew.FP_TEXT)] or list(fp.Pads())
        xs, ys = [], []
        for it in items:
            r = it.GetBoundingBox()
            xs += [pcbnew.ToMM(r.GetLeft()), pcbnew.ToMM(r.GetRight())]
            ys += [pcbnew.ToMM(r.GetTop()), pcbnew.ToMM(r.GetBottom())]
        x0, y1 = min(xs) - ox, max(ys) - oy
        w, h = max(xs) - min(xs) - 0.1, max(ys) - min(ys) - 0.1
        colour = body[2] or LED_COLOR.get(value.get(ref), "#ffffff")
        boxes.append("[%.2f, %.2f, %.2f, %.2f, %s, \"%s\"]" % (x0 + 0.05, Y(y1) + 0.05, w, h, body[1], colour))
    return sorted(boxes)


def usb_lines():
    if REF["usb"]:
        j1 = pos(REF["usb"])
        # USB-C: KiCad rot 270 opens to -X (left edge), rot 90 to +X (right edge)
        return ["USB_Y = %s;" % Y(j1[1]),
                "USB_RIGHT = %s;" % ("true" if j1[2] % 360 == 90 else "false"),
                "USB_FRONT_X = %s;" % round(j1[0] + (3.65 if j1[2] % 360 == 90 else -3.65), 3)]
    # the SuperMini's own USB-C, pointing to the board's front edge (y = 0),
    # which is the far end face of the case
    sm = CASE["supermini"]
    front = round(Y(sm["usb_y"]) + sm["usb_overhang"], 3)
    return ["CASE_USB_END = true;  // SuperMini USB-C in the end face",
            "USB_X = %s;" % sm["x"],
            "USB_FRONT_Y = %s;" % front,
            "USB_Y = 0; USB_RIGHT = false; USB_FRONT_X = 0;  // (side USB unused)",
            "USB_DZ = %s;  // USB-C centre above the carrier top" %
            round(sm["height"] + sm["pcb_t"] + 1.63, 3),
            "CASE_ANT_EXT = %s;  // case end 0.45 mm in front of the USB-C" %
            round(front + 0.45 - (C.BOARD_H + 0.35), 3)]


def case_lines():
    """Board-specific overrides of the case defaults (see case_core.scad)."""
    lines = []
    sm = CASE.get("supermini")
    if sm:
        lines.append("// [x, y of the USB-C edge, USB-C direction, length, width, PCB underside above\n"
                     "//  carrier top, PCB thickness, pin 1 from USB edge, row offset, USB-C overhang]")
        lines.append("SUPERMINI = %s;" % scad([sm["x"], Y(sm["usb_y"]), 90, sm["len"], sm["wid"], sm["height"],
                                               sm["pcb_t"], sm["pin1"], sm["row"], sm["usb_overhang"]]))
    bat = CASE.get("battery")
    if bat:  # pocket under the lid, front end at board y0
        w, length, t = bat["size"]
        lines += ["CASE_BAT = %s;  // pocket under the lid: width, length, thickness" % scad([w, length, t]),
                  "CASE_BAT_LID = %s;" % scad([round((C.BOARD_W - w) / 2, 3), Y(bat["y0"] + length)]),
                  "CASE_BAT_LABEL = %s;" % scad(bat["label"])]
    if "lid_blocks" in CASE:
        lines.append("CASE_LID_BLOCKS = %s;  // [x0, y0, x1, y1, bottom above PCB top]" %
                     scad([[x0, Y(y1), x1, Y(y0), round(z, 3)] for x0, y0, x1, y1, z in CASE["lid_blocks"]]))
    if "led_slits" in CASE:
        names = {"chg": "LED_CHG_XY", "stat": "LED_STAT_XY"}
        lines.append("CASE_LED_SLITS = [%s];" % ", ".join(names[s] for s in CASE["led_slits"]))
    if "pin_buttons" in CASE:
        lines.append("CASE_PIN_BUTTONS = [%s];" % ", ".join(CASE["pin_buttons"]))
    if "windows" in CASE:
        lines.append("CASE_WINDOWS = %s;  // [x0, y0, x1, y1]" %
                     scad([[x0, Y(y1), x1, Y(y0)] for x0, y0, x1, y1 in CASE["windows"]]))
    lines += ["%s = %s;" % (k, scad(v)) for k, v in CASE.get("scad", {}).items()]
    return lines


def main():
    sw1 = pos(REF["switch"])
    bat = pos(REF["bat"])
    swd = pos(REF["swd"])
    src = os.path.basename(sys.modules[C.__name__].__file__)
    lines = [
        "// GENERATED by hardware/gen/make_case_data.py from %s — do not edit." % src,
        "BOARD_W = %s;" % C.BOARD_W,
        "BOARD_H = %s;" % C.BOARD_H,
        "BOARD_R = %s;" % C.CORNER_R,
        "PCB_T = 1.6;",
    ]
    if hasattr(C, "U1_X"):
        lines += [
            # ESP32 module body (18 x 25.5) and its antenna end
            "U1_XY = [%s, %s];" % (C.U1_X, Y(C.U1_Y)),
            "ANTENNA_Y = %s;  // above this Y: antenna, keep metal away" % Y(C.ANTENNA_Y),
            "MODULE_BOTTOM_Y = %s;" % Y(C.MODULE_BOTTOM_Y),
        ]
    lines += usb_lines()
    lines += [
        # slide switch: lever reaches past the board edge (MSK12C02 rot 270 -> left)
        "SW1_Y = %s;" % Y(sw1[1]),
        "SW1_RIGHT = %s;" % ("true" if sw1[0] > C.BOARD_W / 2 else "false"),
        "SW1_LEVER_X = %s;" % round(sw1[0] + (3.35 if sw1[0] > C.BOARD_W / 2 else -3.35), 3),
    ]
    if REF["bat"] != "J2":
        lines.append("// battery socket %s (J2_*), SWD header %s (J3_*)" % (REF["bat"], REF["swd"]))
    lines += [
        # JST-PH battery socket: KiCad rot 0 opens to the port end (-Y), rot 180 to +Y
        "J2_XY = [%s, %s];" % (bat[0], Y(bat[1])),
        "J2_FRONT_Y = %s;" % Y(bat[1] + (-4.4 if bat[2] % 360 == 180 else 4.4)),
        "J2_DIR = %s;" % (1 if bat[2] % 360 == 180 else -1),
        # right-angle SWD header: pin 1 (3V3) at the right, pins run to -X
        "J3_PIN1_X = %s;" % swd[0],
        "J3_ROW_Y = %s;" % Y(swd[1]),
        "J3_TIP_Y = %s;  // pin tips (10.04 mm from the pin row)" % Y(swd[1] + 10.04),
        "J3_PITCH = 2.54;",
        'J3_LABELS = ["3V3", "DIO", "CLK", "RST", "GND"];',
    ]
    if REF["reset"]:
        lines.append("SW2_XY = [%s, %s];  // RESET" % (pos(REF["reset"])[0], Y(pos(REF["reset"])[1])))
    if REF["boot"]:
        lines.append("SW3_XY = [%s, %s];  // BOOT" % (pos(REF["boot"])[0], Y(pos(REF["boot"])[1])))
    if REF["led_stat"]:
        lines.append("LED_STAT_XY = [%s, %s];" % (pos(REF["led_stat"])[0], Y(pos(REF["led_stat"])[1])))
    d2, d3 = (pos(r) for r in REF["led_chg"])
    lines += [
        "LED_CHG_XY = [%s, %s];  // red + green, one window" % (
            round((d2[0] + d3[0]) / 2, 3), Y((d2[1] + d3[1]) / 2)),
        # free spots on the board where lid posts may press the PCB down
        "LID_POSTS = [%s];" % ", ".join("[%s, %s]" % (x, Y(y)) for x, y in C.CASE_POSTS),
    ]
    lines += case_lines()
    lines += [
        "// small parts for the preview renders: [x0, y0, w, h, height, colour]",
        "PARTS = [\n  %s\n];" % ",\n  ".join(part_boxes()),
    ]
    os.makedirs(CASE_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("case data ->", OUT)


if __name__ == "__main__":
    if sys.argv[1:] == ["--paths"]:
        print(CASE_DIR, NAME, DOCS, TITLE)
    elif sys.argv[1:2] == ["--cams"]:
        c = [float(v) for v in sys.argv[2].split(",")]
        for f, part, eye, at in CAMS:
            a = [round(c[i] + at[i], 3) for i in range(3)]
            print(f, part, ",".join("%g" % v for v in [round(a[i] + eye[i], 3) for i in range(3)] + a))
    elif sys.argv[1:] == ["--sheet"]:
        print("|".join(SHEET + (TITLE,)))
    else:
        main()
