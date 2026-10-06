"""Compose the dimensioned view sheet hardware/docs/case-views.png.

make_case.sh renders five orthographic views of the closed case at one common
scale (view-top/-under/-front/-right/-left.png, already trimmed to the case
outline) plus OpenSCAD's echo output with the outer size. This script lays
them out in third-angle projection and draws the overall dimensions.

usage: case_sheet.py <render dir> <out.png>     (needs Pillow)
"""

import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

BG = (248, 248, 248)
INK = (60, 64, 72)
DIM = (200, 90, 20)
FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF", "/Library/Fonts",
             "C:/Windows/Fonts"]


def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"] if bold else \
        ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"]
    for d in FONT_DIRS:
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def text_c(draw, xy, s, f, fill=INK):  # centred text
    l, t, r, b = draw.textbbox((0, 0), s, font=f)
    draw.text((xy[0] - (r - l) / 2 - l, xy[1] - (b - t) / 2 - t), s, font=f, fill=fill)


def arrow(draw, tip, d):  # d = unit direction the arrow points to
    ux, uy = d
    a, w = 16, 6
    bx, by = tip[0] - ux * a, tip[1] - uy * a
    draw.polygon([tip, (bx - uy * w, by + ux * w), (bx + uy * w, by - ux * w)], fill=DIM)


def dim_h(img, x0, x1, y, ref_y, label, f):
    """Horizontal dimension x0..x1 drawn at y; extension lines go to ref_y."""
    d = ImageDraw.Draw(img)
    for x in (x0, x1):
        d.line([(x, ref_y), (x, y + (8 if y > ref_y else -8))], fill=DIM, width=2)
    d.line([(x0, y), (x1, y)], fill=DIM, width=3)
    arrow(d, (x0, y), (-1, 0))
    arrow(d, (x1, y), (1, 0))
    text_c(d, ((x0 + x1) / 2, y - 22), label, f, DIM)


def dim_v(img, y0, y1, x, ref_x, label, f):
    """Vertical dimension y0..y1 drawn at x; extension lines go to ref_x."""
    d = ImageDraw.Draw(img)
    for y in (y0, y1):
        d.line([(ref_x, y), (x + (8 if x > ref_x else -8), y)], fill=DIM, width=2)
    d.line([(x, y0), (x, y1)], fill=DIM, width=3)
    arrow(d, (x, y0), (0, -1))
    arrow(d, (x, y1), (0, 1))
    l, t, r, b = d.textbbox((0, 0), label, font=f)
    tile = Image.new("RGBA", (r - l + 8, b - t + 8), BG + (0,))
    ImageDraw.Draw(tile).text((4 - l, 4 - t), label, font=f, fill=DIM)
    tile = tile.rotate(90, expand=True)
    img.paste(tile, (int(x - tile.width - 10), int((y0 + y1) / 2 - tile.height / 2)), tile)


def main():
    src, out = sys.argv[1], sys.argv[2]
    echo = open(os.path.join(src, "case.echo")).read()
    w_mm, l_mm, h_mm = (float(v) for v in re.search(r"CASE_SIZE = \[([^\]]*)\]", echo).group(1).split(","))
    v = {k: Image.open(os.path.join(src, "view-%s.png" % k)).convert("RGB")
         for k in ("top", "under", "front", "right", "left")}
    # side views: rotate so the port end (-Y) is at the bottom, like the top view
    v["right"] = v["right"].rotate(90, expand=True)
    v["left"] = v["left"].rotate(-90, expand=True)
    px_mm = v["top"].width / w_mm

    f_dim, f_cap, f_title, f_note = font(30, True), font(28, True), font(40, True), font(24)
    gap, cap = 110, 60
    top, side, front = v["top"], v["left"], v["front"]
    x_left = 150
    x_top = x_left + side.width + gap
    x_right = x_top + top.width + gap
    x_under = x_right + side.width + gap + 60
    y_top = 230
    y_front = y_top + top.height + cap + 70
    W = x_under + top.width + 170
    H = y_front + front.height + cap + 170
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    img.paste(v["left"], (x_left, y_top))
    img.paste(top, (x_top, y_top))
    img.paste(v["right"], (x_right, y_top))
    img.paste(v["under"], (x_under, y_top))
    img.paste(front, (x_top, y_front))

    cy = y_top + top.height + 34
    text_c(d, (x_left + side.width / 2, cy), "Schalter", f_cap)
    text_c(d, (x_top + top.width / 2, cy), "Oben", f_cap)
    text_c(d, (x_right + side.width / 2, cy), "USB-C", f_cap)
    text_c(d, (x_under + top.width / 2, cy), "Unten", f_cap)
    text_c(d, (x_top + front.width / 2, y_front + front.height + 34), "Stirnseite SWD", f_cap)

    fmt = lambda mm: ("%.1f" % mm).replace(".", ",")  # noqa: E731
    dim_h(img, x_top, x_top + top.width, y_top - 50, y_top, fmt(w_mm), f_dim)
    dim_v(img, y_top, y_top + top.height, x_left - 50, x_left, fmt(l_mm), f_dim)
    dim_h(img, x_right, x_right + side.width, y_top - 50, y_top, fmt(h_mm), f_dim)
    dim_v(img, y_front, y_front + front.height, x_top - 50, x_top, fmt(h_mm), f_dim)

    d.text((x_left - 100, 40), "X3-Tuner Gehäuse", font=f_title, fill=INK)
    d.text((x_left - 100, 98), "Maße in mm, alle Ansichten im gleichen Maßstab "
           "(%.1f px/mm). Port-Ende (SWD) jeweils unten." % px_mm, font=f_note, fill=INK)
    img.save(out, optimize=True)
    print("view sheet ->", out, "(%dx%d)" % (W, H))


if __name__ == "__main__":
    main()
