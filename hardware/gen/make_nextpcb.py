"""Single board with break-off side rails for NextPCB's "Rev 0" offer.

NextPCB assembles the first order for free, but only for boards of at least
50 x 50 mm. The X3-Tuner is 38 x 54.5 mm, so this adds a 4 mm rail on the left
and right (3 mm milled gap, mouse-bite tabs from circuit.PANEL_TABS): 52 x
54.5 mm. The rails snap off after assembly like on the 10-up panel.

Writes production/nextpcb/: Gerber zip, CPL and an MPN BOM (NextPCB sources
the parts from its HQ Online store, which does not use LCSC numbers).
Needs KiKit — set KIKIT=/path/to/kikit.
"""

import csv
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
from make_fab import natural  # noqa: E402
from make_panel import HW, KIKIT, SRC, drc, fab  # noqa: E402

PDIR = os.path.join(HW, "kicad", "nextpcb")
BOARD = os.path.join(PDIR, C.PROJECT + "-rails.kicad_pcb")
OUT = os.path.join(HW, "production", "nextpcb")
NAME = C.PROJECT + "-nextpcb"


def panelize():
    os.makedirs(PDIR, exist_ok=True)
    subprocess.run([
        KIKIT, "panelize",
        "--layout", "grid; rows: 1; cols: 1; renameref: {orig}",
        "--tabs", "annotation",
        "--cuts", "mousebites; drill: 0.5mm; spacing: 0.8mm; offset: 0.2mm; prolong: 0.5mm",
        "--framing", "railslr; width: 4mm; space: 3mm",
        "--post", "millradius: 1mm; refillzones: true",
        SRC, BOARD,
    ], check=True, capture_output=True)


def mpn_bom(groups):
    out = os.path.join(OUT, NAME + "-bom.csv")
    parts = {p.ref: p for p in C.PARTS}
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Qty", "Value", "Package", "Manufacturer", "MPN", "Description"])
        for (value, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: natural(kv[1][0])):
            refs = sorted(refs, key=natural)
            p = parts[refs[0]]
            mfr, mpn = C.MPN.get(lcsc, ("", ""))
            desc = ("Widerstand 1 %, Dickschicht" if p.sym == "Device:R" else
                    "MLCC X5R/X7R, >= 10 V" if p.sym == "Device:C" else p.desc)
            w.writerow([",".join(refs), len(refs), value, fp, mfr, mpn or value, desc])
    return out


def main():
    panelize()
    kinds, size = drc(BOARD)
    print("rails board %.1f x %.1f mm, DRC: %s" % (size[0], size[1], kinds or "clean"))
    # NextPCB places by the KiCad/IPC orientation, so no JLC rotation fixes
    z, n, groups = fab(BOARD, OUT, NAME, rot_fix=())
    os.remove(os.path.join(OUT, NAME + "-bom.csv"))  # JLC format; NextPCB gets MPNs instead
    print("nextpcb ->", os.path.relpath(z, HW), "+", os.path.basename(mpn_bom(groups)),
          "+ cpl (%d placements)" % n)


if __name__ == "__main__":
    main()
