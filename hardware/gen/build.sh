#!/usr/bin/env bash
# Regenerate the complete X3-Tuner hardware from hardware/gen/circuit.py:
# schematic -> netlist check -> placement -> Freerouting -> pours/stitching ->
# DRC -> fabrication files (Gerber, drill, BOM, CPL) -> preview images.
#
# Needs: KiCad 7 (kicad-cli + pcbnew Python), Java 17+, xvfb-run, rsvg-convert,
# ImageMagick, and freerouting-1.9.0.jar (set FREEROUTING=/path/to/jar).
set -euo pipefail
cd "$(dirname "$0")"
FREEROUTING="${FREEROUTING:-/tmp/freerouting.jar}"
PASSES="${PASSES:-60}"
K=../kicad

python3 make_sch.py
python3 check_netlist.py
python3 make_pcb.py place
python3 make_pcb.py dsn
if [[ "${SKIP_ROUTE:-0}" != "1" ]]; then
  (cd "$K" && xvfb-run -a java -jar "$FREEROUTING" -de x3tuner.dsn -do x3tuner.ses \
      -mp "$PASSES" -mt 1 2>&1 | grep -E "INFO|WARN" | grep -v -E "Settings|FRAnalytics" || true)
fi
python3 make_pcb.py ses
python3 drc.py
python3 make_fab.py
