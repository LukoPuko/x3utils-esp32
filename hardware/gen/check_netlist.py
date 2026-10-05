"""Compare the netlist KiCad derives from the schematic with circuit.py."""
import os, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import circuit as C
from sexpr import parse, find, find_all
KDIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kicad"))
out = os.path.join(tempfile.mkdtemp(), "n.net")
subprocess.run(["kicad-cli", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out,
                os.path.join(KDIR, C.PROJECT + ".kicad_sch")], check=True, capture_output=True)
tree = parse(open(out).read())[0]
got = {}
for n in find_all(find(tree, "nets"), "net"):
    name = str(find(n, "name")[1]).lstrip("/")
    for node in find_all(n, "node"):
        ref, pin = str(find(node, "ref")[1]), str(find(node, "pin")[1])
        if ref.startswith("#"):
            continue
        got[(ref, pin)] = name
want = {(p.ref, num): net for p in C.PARTS for num, net in p.pins.items() if net}
errors = 0
for k, v in sorted(want.items()):
    if got.get(k) != v:
        print("MISMATCH", k, "want", v, "got", got.get(k)); errors += 1
for k, v in sorted(got.items()):
    if k not in want and not v.startswith("unconnected-"):
        print("EXTRA", k, v); errors += 1
print("netlist check: %d pins, %d errors" % (len(want), errors))
sys.exit(1 if errors else 0)
