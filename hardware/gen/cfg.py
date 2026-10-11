"""Which board the generator scripts build.

X3_CIRCUIT selects the circuit module: "circuit" (X3-Tuner, the default) or
"circuit_carrier" (carrier board for a plug-in ESP32-C3 SuperMini). Each board
has its own kicad/, production/ and docs/ folders below hardware/C.SUBDIR.
"""

import importlib
import os
import sys

GEN = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, GEN)

C = importlib.import_module(os.environ.get("X3_CIRCUIT", "circuit"))
HW = os.path.normpath(os.path.join(GEN, ".."))
BASE = os.path.normpath(os.path.join(HW, getattr(C, "SUBDIR", ".")))
KDIR = os.path.join(BASE, "kicad")
PROD = os.path.join(BASE, "production")
DOCS = os.path.join(BASE, "docs")
# project footprint libraries shared by all boards (x3tuner.pretty, kikit.pretty)
LIBDIR = os.path.join(HW, "kicad")
LOCAL_LIBS = ("x3tuner", "kikit")

if __name__ == "__main__":  # used by build.sh
    print(C.PROJECT, KDIR)
