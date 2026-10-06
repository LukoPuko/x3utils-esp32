#!/usr/bin/env bash
# Build the 3D-printable case: board_data.scad from circuit.py, STL files and
# the preview renders in hardware/docs/. Needs OpenSCAD (2021.01+), xvfb-run,
# ImageMagick, and Python with Pillow for the dimensioned view sheet.
set -euo pipefail
cd "$(dirname "$0")"
python3 make_case_data.py
CASE=../case
SCAD="$CASE/x3tuner_case.scad"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$CASE/stl" ../docs
for p in bottom lid print; do
  openscad -q -o "$CASE/stl/x3tuner-case-$p.stl" -D "part=\"$p\"" "$SCAD"
done
python3 stl_binary.py "$CASE"/stl/*.stl
openscad -o "$TMP/case.echo" -D 'part="none"' "$SCAD" 2>/dev/null  # -q would drop the echo

# Perspective renders: drawn at 2x and scaled down (smooth edges), cropped to
# the object. USE_STL makes the previews import the STLs written above.
r() {
  local out=$1; shift
  xvfb-run -a openscad -q -o "$TMP/$out" -D USE_STL=true --imgsize=2800,2000 \
    --colorscheme=Tomorrow "$@" "$SCAD"
  local bg; bg=$(convert "$TMP/$out" -format '%[pixel:p{0,0}]' info:)
  convert "$TMP/$out" -trim +repage -resize 1400x1400 -bordercolor "$bg" -border 30 "../docs/$out"
}
r case-assembly.png     -D 'part="assembly"' --camera=70,-55,65,19,28,6 --viewall
r case-xray.png         -D 'part="xray"'     --camera=70,-55,65,19,28,6 --viewall
r case-xray-bottom.png  -D 'part="xray"'     --camera=-60,-50,-55,19,28,6 --viewall
r case-section.png      -D 'part="section"'  --camera=95,70,35,19,26,7 --viewall
r case-exploded.png     -D 'part="exploded"' --camera=70,-70,70,19,28,14 --viewall

# Orthographic views at one fixed scale for the dimensioned sheet
C=$(sed -n 's/.*CASE_CENTER = \[\([^]]*\)\].*/\1/p' "$TMP/case.echo" | tr -d ' ')
v() {
  xvfb-run -a openscad -q -o "$TMP/view-$1.png" -D 'part="assembly"' -D USE_STL=true \
    --projection=o --imgsize=1600,1600 --colorscheme=Tomorrow --camera="$C,$2,400" "$SCAD"
  convert "$TMP/view-$1.png" -trim +repage "$TMP/view-$1.png"
}
v top 0,0,0; v under 0,180,0; v front 90,0,0; v right 90,0,90; v left 90,0,270
PY=""
for p in python3 python3.12 python3.11 python; do
  if command -v "$p" >/dev/null && "$p" -c 'import PIL.Image' 2>/dev/null; then PY=$p; break; fi
done
if [[ -n "$PY" ]]; then "$PY" case_sheet.py "$TMP" ../docs/case-views.png
else echo "Pillow not found: skipping docs/case-views.png"; fi
echo "case -> hardware/case/stl/, renders -> hardware/docs/case-*.png"
