import pcbnew, sys
sys.path.insert(0,'.')
from make_pcb import PCB, OX, OY
b = pcbnew.LoadBoard(PCB)
boxes = {}
for fp in b.GetFootprints():
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount() == 0:
        bb = fp.GetBoundingBox(False, False)
    else:
        bb = cy.BBox()
    x0 = pcbnew.ToMM(bb.GetX()) - OX; y0 = pcbnew.ToMM(bb.GetY()) - OY
    x1 = x0 + pcbnew.ToMM(bb.GetWidth()); y1 = y0 + pcbnew.ToMM(bb.GetHeight())
    boxes[fp.GetReference()] = (x0, y0, x1, y1)
for r, (x0, y0, x1, y1) in sorted(boxes.items()):
    if len(sys.argv) > 1 and r not in sys.argv[1:]: continue
    print("%-4s x %6.2f..%6.2f  y %6.2f..%6.2f" % (r, x0, x1, y0, y1))
print("overlaps:")
refs = sorted(boxes)
for i, a in enumerate(refs):
    for c in refs[i+1:]:
        A, B = boxes[a], boxes[c]
        if a == "U1" or c == "U1":
            # module courtyard includes antenna keep-out; only check below antenna
            pass
        if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
            print("  ", a, c)
