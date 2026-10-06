"""Convert OpenSCAD's ASCII STL output to binary STL (about 5x smaller)."""
import struct
import sys

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
    print("%s: %d triangles (binary)" % (path, len(tris)))
