"""Production panel (5 x 2 = 10 boards) for volume orders.

JLCPCB's cheap "Economic" assembly takes 2-50 pieces per order, and its
"Standard" assembly needs boards >= 70 x 70 mm. A 10-up panel fixes both:
100 / 200 / 500 boards = 10 / 20 / 50 panels, all still Economic PCBA.

Layout: 5 columns x 2 rows, 3 mm milled gaps with mouse-bite tabs (kept away
from the USB-C and switch overhangs), the top row rotated 180 deg so every SWD
header edge faces a rail. Rails top/bottom carry 3 fiducials, 3 tooling holes
and a label. Panel size about 202 x 139 mm.

Needs KiKit (https://github.com/yaqwsx/KiKit) — set KIKIT=/path/to/kikit.
Writes production/panel/*: Gerber zip, BOM, CPL (quantity is in panels).
"""

import collections
import csv
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
from make_fab import GERBER_LAYERS, ROT_FIX, natural, run  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(HW, "kicad", C.PROJECT + ".kicad_pcb")
PDIR = os.path.join(HW, "kicad", "panel")
PANEL = os.path.join(PDIR, C.PROJECT + "-panel.kicad_pcb")
OUT = os.path.join(HW, "production", "panel")
KIKIT = os.environ.get("KIKIT", "kikit")

COLS, ROWS = 5, 2


def panelize():
    os.makedirs(PDIR, exist_ok=True)
    subprocess.run([
        KIKIT, "panelize",
        "--layout", "grid; rows: %d; cols: %d; space: 3mm; rotation: 180deg; "
                    "alternation: rows; renameref: {orig}_{n}" % (ROWS, COLS),
        # tab positions come from the kikit:Tab annotations (circuit.PANEL_TABS)
        "--tabs", "annotation",
        "--cuts", "mousebites; drill: 0.5mm; spacing: 0.8mm; offset: 0.2mm; prolong: 0.5mm",
        "--framing", "railstb; width: 5mm; space: 3mm",
        "--tooling", "3hole; hoffset: 2.5mm; voffset: 2.5mm; size: 1.152mm",
        "--fiducials", "3fid; hoffset: 8mm; voffset: 2.5mm; coppersize: 1mm; opening: 2mm",
        "--text", "simple; text: X3-Tuner v%s - panel %dx%d; anchor: mt; voffset: 2.5mm; "
                  "hjustify: center; vjustify: center" % (C.REV, COLS, ROWS),
        "--post", "millradius: 1mm; refillzones: true",
        SRC, PANEL,
    ], check=True, capture_output=True)


def drc():
    board = pcbnew.LoadBoard(PANEL)
    rep = os.path.join(PDIR, "drc_report.txt")
    pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(rep).read()
    kinds = collections.Counter(re.findall(r"^\[(\w+)\]", txt, re.M))
    bb = board.GetBoardEdgesBoundingBox()
    return dict(kinds), (pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))


def fab():
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp()
    run("kicad-cli", "pcb", "export", "gerbers", "--layers", GERBER_LAYERS,
        "--subtract-soldermask", "--no-x2", "-o", tmp + "/", PANEL)
    run("kicad-cli", "pcb", "export", "drill", "--format", "excellon",
        "--excellon-units", "mm", "--excellon-separate-th", "-o", tmp + "/", PANEL)
    import zipfile
    zpath = os.path.join(OUT, C.PROJECT + "-panel-gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(tmp)):
            z.write(os.path.join(tmp, f), f)

    parts = {p.ref: p for p in C.PARTS}
    pos = os.path.join(tmp, "pos.csv")
    run("kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "front", "-o", pos, PANEL)
    groups = {}
    with open(pos) as fi, open(os.path.join(OUT, C.PROJECT + "-panel-cpl.csv"), "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(fi):
            ref = row["Ref"]
            p = parts.get(ref.rsplit("_", 1)[0])
            if p is None or not p.bom or not p.lcsc:
                continue
            rot = float(row["Rot"])
            for pat, add in ROT_FIX:
                if re.search(pat, row["Package"]):
                    rot += add
            rot %= 360
            w.writerow([ref, "%.4fmm" % float(row["PosX"]), "%.4fmm" % float(row["PosY"]),
                        "Top", "%g" % rot])
            groups.setdefault((p.value, p.fp.split(":")[1], p.lcsc), []).append(ref)
    with open(os.path.join(OUT, C.PROJECT + "-panel-bom.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: natural(kv[1][0])):
            w.writerow([value, ",".join(sorted(refs, key=natural)), fp, lcsc])
    shutil.rmtree(tmp)
    return zpath, sum(len(r) for r in groups.values())


def render():
    from render import PX_PER_MM  # noqa: F401  (same toolchain as the board renders)
    svg = os.path.join(PDIR, "panel.svg")
    png = os.path.join(HW, "docs", "panel-top.png")
    run("kicad-cli", "pcb", "export", "svg", "--layers", "F.Cu,F.SilkS,F.Mask,Edge.Cuts",
        "--exclude-drawing-sheet", "--page-size-mode", "2", "-o", svg, PANEL)
    run("rsvg-convert", "-z", "2.5", "-b", "white", svg, "-o", png)
    os.remove(svg)
    return png


def main():
    panelize()
    kinds, size = drc()
    print("panel %.1f x %.1f mm, DRC: %s" % (size[0], size[1], kinds or "clean"))
    z, n = fab()
    print("panel fab ->", os.path.relpath(z, HW), "(%d placements per panel)" % n)
    print("render ->", os.path.relpath(render(), HW))


if __name__ == "__main__":
    main()
