"""Render the PCB to cropped PNGs (top/bottom/assembly) via kicad-cli + rsvg."""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
from make_pcb import OX, OY, PCB  # noqa: E402

PX_PER_MM = 96 / 25.4


def render(layers, out_png, zoom=8, margin=4, mirror=False, theme=None):
    svg = out_png[:-4] + ".svg"
    cmd = ["kicad-cli", "pcb", "export", "svg", "--layers", layers,
           "--exclude-drawing-sheet", "--page-size-mode", "0", "-o", svg, PCB]
    if mirror:
        cmd.insert(4, "--mirror")
    if theme:
        cmd[4:4] = ["--theme", theme]
    subprocess.run(cmd, check=True, capture_output=True)
    full = out_png[:-4] + "_full.png"
    subprocess.run(["rsvg-convert", "-z", str(zoom), "-b", "white", svg, "-o", full], check=True)
    s = PX_PER_MM * zoom
    x0, x1 = OX - margin, OX + C.BOARD_W + margin
    if mirror:  # A4 landscape page is 297 mm wide
        x0, x1 = 297 - (OX + C.BOARD_W + margin), 297 - (OX - margin)
    box = (int(x0 * s), int((OY - margin) * s), int(x1 * s), int((OY + C.BOARD_H + margin) * s))
    w, h = box[2] - box[0], box[3] - box[1]
    subprocess.run(["convert", full, "-crop", "%dx%d+%d+%d" % (w, h, box[0], box[1]),
                    "+repage", out_png], check=True)
    os.remove(full)
    os.remove(svg)
    return out_png


if __name__ == "__main__":
    out = sys.argv[1]
    which = sys.argv[2] if len(sys.argv) > 2 else "top"
    if which == "top":
        render("F.Cu,F.SilkS,F.Mask,Edge.Cuts", out)
    elif which == "bottom":
        render("B.Cu,B.SilkS,Edge.Cuts", out, mirror=True)
    elif which == "place":
        render("F.Cu,F.SilkS,F.CrtYd,Edge.Cuts,F.Fab", out)
    elif which == "both":
        render("F.Cu,B.Cu,F.SilkS,Edge.Cuts", out)
