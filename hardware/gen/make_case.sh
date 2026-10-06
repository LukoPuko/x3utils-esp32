#!/usr/bin/env bash
# Build the 3D-printable case: board_data.scad from circuit.py, STL files and
# preview renders. Needs OpenSCAD (2021.01+) and xvfb-run for the PNGs.
set -euo pipefail
cd "$(dirname "$0")"
python3 make_case_data.py
CASE=../case
mkdir -p "$CASE/stl" ../docs
for p in bottom lid print; do
  openscad -q -o "$CASE/stl/x3tuner-case-$p.stl" -D "part=\"$p\"" "$CASE/x3tuner_case.scad"
done
python3 stl_binary.py "$CASE"/stl/*.stl
r() { xvfb-run -a openscad -q -o "../docs/$1" -D "part=\"$2\"" --imgsize=1400,1000 \
        --colorscheme=Tomorrow "${@:3}" "$CASE/x3tuner_case.scad"; }
r case-assembly.png assembly --camera=60,-70,75,19,27,8 --viewall
r case-exploded.png exploded --camera=60,-70,85,19,27,12 --viewall
r case-lid.png lid --camera=19,27,120,19,27,0 --viewall
r case-bottom.png bottom --camera=-40,-60,90,19,27,4 --viewall
for f in ../docs/case-*.png; do  # trim the empty background, keep a margin
  bg=$(convert "$f" -format '%[pixel:p{0,0}]' info:)
  convert "$f" -trim +repage -bordercolor "$bg" -border 30 "$f"
done
echo "case -> hardware/case/stl/, renders -> hardware/docs/case-*.png"
