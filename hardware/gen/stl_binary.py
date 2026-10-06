"""Convert OpenSCAD's ASCII STL output to binary STL (about 5x smaller) and
check that every mesh is closed (each edge shared by exactly two triangles,
once in each direction), i.e. prints without slicer repairs."""
import struct
import sys
from collections import Counter

bad_files = 0

for path in sys.argv[1:]:
    tris, normal, verts = [], None, []
    with open(path) as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            if t[0] == "facet":
                normal = tuple(map(float, t[2:5]))
                verts = []
            elif t[0] == "vertex":
                verts.append(tuple(map(float, t[1:4])))
            elif t[0] == "endfacet":
                tris.append((normal, verts))
    with open(path, "wb") as f:
        f.write(b"x3tuner case".ljust(80, b" "))
        f.write(struct.pack("<I", len(tris)))
        for n, v in tris:
            f.write(struct.pack("<12fH", *n, *v[0], *v[1], *v[2], 0))
    edges = Counter()
    for _, v in tris:
        for a, b in ((v[0], v[1]), (v[1], v[2]), (v[2], v[0])):
            edges[(a, b)] += 1
    bad = sum(1 for (a, b), n in edges.items() if n != 1 or edges.get((b, a)) != 1)
    bad_files += bad > 0
    print("%s: %d triangles (binary), %s" % (path, len(tris),
                                            "manifold" if not bad else "%d open/non-manifold edges" % bad))

sys.exit(1 if bad_files else 0)
