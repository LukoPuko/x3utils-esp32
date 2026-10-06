"""Fabrication outputs for JLCPCB (PCB + SMT assembly) and documentation images.

  production/x3tuner-gerbers.zip   Gerber + Excellon drill (upload as-is)
  production/x3tuner-bom.csv       JLCPCB BOM  (Comment, Designator, Footprint, LCSC)
  production/x3tuner-cpl.csv       JLCPCB CPL  (Designator, Mid X, Mid Y, Layer, Rotation)
  docs/x3tuner-schematic.pdf, docs/pcb-*.png
"""

import csv
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
from render import render  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(HERE, ".."))
KDIR = os.path.join(HW, "kicad")
PROD = os.path.join(HW, "production")
DOCS = os.path.join(HW, "docs")
PCB = os.path.join(KDIR, C.PROJECT + ".kicad_pcb")
SCH = os.path.join(KDIR, C.PROJECT + ".kicad_sch")

# JLCPCB's placement machines use a different zero orientation than KiCad for
# some packages. Values from the community-maintained table used by the
# kicad-jlcpcb-tools plugin; always check the 3D preview in the JLC order.
ROT_FIX = [
    (r"^SOT-23", 180),
    (r"^SOIC-", 270),
    (r"^TSSOP-", 270),
    (r"^JST_PH_S2B-PH-SM4-TB", 180),
]

GERBER_LAYERS = "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts"


def run(*cmd):
    subprocess.run(cmd, check=True, capture_output=True)


def gerbers():
    tmp = tempfile.mkdtemp()
    run("kicad-cli", "pcb", "export", "gerbers", "--layers", GERBER_LAYERS,
        "--subtract-soldermask", "--no-x2", "-o", tmp + "/", PCB)
    run("kicad-cli", "pcb", "export", "drill", "--format", "excellon",
        "--excellon-units", "mm", "--excellon-separate-th", "-o", tmp + "/", PCB)
    out = os.path.join(PROD, C.PROJECT + "-gerbers.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(glob.glob(tmp + "/*")):
            z.write(f, os.path.basename(f))
    names = sorted(os.path.basename(f) for f in glob.glob(tmp + "/*"))
    shutil.rmtree(tmp)
    return out, names


def bom():
    groups = {}
    for p in C.PARTS:
        if not p.bom or not p.lcsc:
            continue
        key = (p.value, p.fp.split(":")[1], p.lcsc)
        groups.setdefault(key, []).append(p.ref)
    out = os.path.join(PROD, C.PROJECT + "-bom.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: natural(kv[1][0])):
            w.writerow([value, ",".join(sorted(refs, key=natural)), fp, lcsc])
    return out, sum(len(r) for r in groups.values()), len(groups)


def bom_generic():
    """Assembler-neutral BOM (for NextPCB, PCBWay, ... quotes)."""
    groups = {}
    for p in C.PARTS:
        if not p.bom or not p.lcsc:
            continue
        key = (p.value, p.fp.split(":")[1], p.lcsc)
        groups.setdefault(key, []).append(p)
    out = os.path.join(PROD, C.PROJECT + "-bom-generic.csv")
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Qty", "Value", "Package", "Manufacturer", "MPN", "LCSC", "Description"])
        for (value, fp, lcsc), parts in sorted(groups.items(), key=lambda kv: natural(kv[1][0].ref)):
            mfr, mpn = C.MPN.get(lcsc, ("", ""))
            refs = sorted((p.ref for p in parts), key=natural)
            sym = parts[0].sym
            desc = ("Widerstand 1 %, Dickschicht" if sym == "Device:R" else
                    "MLCC X5R/X7R, >= 10 V" if sym == "Device:C" else parts[0].desc)
            w.writerow([",".join(refs), len(refs), value, fp, mfr, mpn, lcsc, desc])
    return out


def natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def cpl():
    tmp = tempfile.mkdtemp()
    pos = os.path.join(tmp, "pos.csv")
    run("kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm",
        "--side", "front", "-o", pos, PCB)
    parts = {p.ref: p for p in C.PARTS}
    out = os.path.join(PROD, C.PROJECT + "-cpl.csv")
    n = 0
    with open(pos) as fi, open(out, "w", newline="") as fo:
        w = csv.writer(fo)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for row in csv.DictReader(fi):
            ref = row["Ref"]
            p = parts.get(ref)
            if p is None or not p.bom or not p.lcsc:
                continue
            rot = float(row["Rot"])
            pkg = row["Package"]
            for pat, add in ROT_FIX:
                if re.search(pat, pkg):
                    rot += add
            rot %= 360
            w.writerow([ref, "%.4fmm" % float(row["PosX"]), "%.4fmm" % float(row["PosY"]),
                        "Top", "%g" % rot])
            n += 1
    shutil.rmtree(tmp)
    return out, n


def docs():
    pdf = os.path.join(DOCS, C.PROJECT + "-schematic.pdf")
    run("kicad-cli", "sch", "export", "pdf", "-o", pdf, SCH)
    run("pdftoppm", "-r", "150", "-png", "-singlefile", pdf, os.path.join(DOCS, "schematic"))
    run("kicad-cli", "pcb", "export", "pdf", "--layers", "F.Fab,F.CrtYd,Edge.Cuts,F.SilkS",
        "-o", os.path.join(DOCS, C.PROJECT + "-assembly.pdf"), PCB)
    render("F.Cu,F.SilkS,F.Mask,Edge.Cuts", os.path.join(DOCS, "pcb-top.png"), zoom=6)
    render("B.Cu,B.SilkS,B.Mask,Edge.Cuts", os.path.join(DOCS, "pcb-bottom.png"), zoom=6, mirror=True)
    render("F.Fab,F.SilkS,Edge.Cuts", os.path.join(DOCS, "pcb-assembly.png"), zoom=6)


def main():
    os.makedirs(PROD, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    z, names = gerbers()
    print("gerbers ->", os.path.relpath(z, HW), "(%d files)" % len(names))
    b, n, lines = bom()
    print("bom     ->", os.path.relpath(b, HW), "(%d parts, %d lines)" % (n, lines))
    print("bom     ->", os.path.relpath(bom_generic(), HW), "(assembler-neutral)")
    c, n = cpl()
    print("cpl     ->", os.path.relpath(c, HW), "(%d placements)" % n)
    docs()
    print("docs    -> docs/")


if __name__ == "__main__":
    main()
