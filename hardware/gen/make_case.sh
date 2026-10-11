#!/usr/bin/env bash
# Build the 3D-printable case: board_data.scad from the circuit file, STL files
# and the preview renders in the board's docs/ folder. Needs OpenSCAD
# (2021.01+), xvfb-run, ImageMagick, and Python with Pillow for the dimensioned
# view sheet. The board comes from X3_CIRCUIT (see cfg.py):
#   make_case.sh                                  X3-Tuner  -> hardware/case/
#   X3_CIRCUIT=circuit_carrier make_case.sh       X3-Tuner Mini -> hardware/carrier/case/
set -euo pipefail
cd "$(dirname "$0")"
python3 make_case_data.py
read -r CASE NAME DOCS TITLE < <(python3 make_case_data.py --paths)
SCAD="$CASE/${NAME}_case.scad"
STL="$CASE/stl/$NAME-case"
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$CASE/stl" "$DOCS"
for p in bottom lid print; do
  openscad -q -o "$STL-$p.stl" -D "part=\"$p\"" "$SCAD"
done
python3 stl_binary.py "$STL"-*.stl
openscad -o "$TMP/case.echo" -D 'part="none"' "$SCAD" 2>/dev/null  # -q would drop the echo
# centre of the case for the cameras below
C=$(sed -n 's/.*CASE_CENTER = \[\([^]]*\)\].*/\1/p' "$TMP/case.echo" | tr -d ' ')

# Perspective renders: drawn at 2x and scaled down (smooth edges), cropped to
# the object. USE_STL makes the previews import the STLs written above.
r() {
  local out=$1; shift
  xvfb-run -a openscad -q -o "$TMP/$out" -D USE_STL=true -D "STL_PREFIX=\"$STL-\"" \
    --imgsize=2800,2000 --colorscheme=Tomorrow "$@" "$SCAD"
  local bg; bg=$(convert "$TMP/$out" -format '%[pixel:p{0,0}]' info:)
  convert "$TMP/$out" -trim +repage -resize 1400x1400 -bordercolor "$bg" -border 30 "$DOCS/$out"
}
# cameras per board: make_case_data.py --cams (eye + look-at point)
while read -r out part cam; do
  r "$out" -D "part=\"$part\"" --camera="$cam" --viewall </dev/null
done < <(python3 make_case_data.py --cams "$C")

# Orthographic views at one fixed scale for the dimensioned sheet
v() {
  xvfb-run -a openscad -q -o "$TMP/view-$1.png" -D 'part="assembly"' -D USE_STL=true \
    -D "STL_PREFIX=\"$STL-\"" --projection=o --imgsize=1600,1600 --colorscheme=Tomorrow \
    --camera="$C,$2,400" "$SCAD"
  convert "$TMP/view-$1.png" -trim +repage "$TMP/view-$1.png"
}
v top 0,0,0; v under 0,180,0; v front 90,0,0; v right 90,0,90; v left 90,0,270; v back 90,0,180
PY=""
for p in python3 python3.12 python3.11 python; do
  if command -v "$p" >/dev/null && "$p" -c 'import PIL.Image' 2>/dev/null; then PY=$p; break; fi
done
if [[ -n "$PY" ]]; then "$PY" case_sheet.py "$TMP" "$DOCS/case-views.png" "$(python3 make_case_data.py --sheet)"
else echo "Pillow not found: skipping $DOCS/case-views.png"; fi
echo "case -> $CASE/stl/, renders -> $DOCS/case-*.png"
