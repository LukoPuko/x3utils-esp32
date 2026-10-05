import os, sys, re, collections
import pcbnew
sys.path.insert(0, os.path.dirname(__file__))
from make_pcb import PCB, KDIR
b = pcbnew.LoadBoard(PCB)
rep = os.path.join(KDIR, "drc_report.txt")
pcbnew.WriteDRCReport(b, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(rep).read()
kinds = collections.Counter(re.findall(r"^\[(\w+)\]", txt, re.M))
print(dict(kinds))
for line in txt.splitlines():
    if line.startswith("**"):
        print(line)
if len(sys.argv) > 1:
    print(txt[:int(sys.argv[1])])
