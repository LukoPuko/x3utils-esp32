"""Build the X3-Tuner PCB with the KiCad 7 pcbnew Python API.

Stages (run by build.sh):
  place   – create board, outline, footprints, nets, keep-outs  -> .kicad_pcb
  dsn     – export Specctra DSN for Freerouting
  ses     – import Freerouting's SES routes, add GND pours, stitch, fill, DRC
"""

import json
import math
import os
import sys
import uuid

import pcbnew

sys.path.insert(0, os.path.dirname(__file__))
import circuit as C  # noqa: E402
import sexpr  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KDIR = os.path.normpath(os.path.join(HERE, "..", "kicad"))
PCB = os.path.join(KDIR, C.PROJECT + ".kicad_pcb")
PRO = os.path.join(KDIR, C.PROJECT + ".kicad_pro")
FPROOT = "/usr/share/kicad/footprints"

# Sheet offset so the board sits nicely on the A4 drawing.
OX, OY = 100.0, 60.0


def mm(v):
    return pcbnew.FromMM(v)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def sym_uuid(ref):
    # Stable UUIDs shared with the schematic generator (links PCB <-> SCH).
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "x3tuner/" + ref))


# ── project file: net classes + JLCPCB-safe design rules ─────────────────────
def write_project():
    pro = {
        "board": {
            "design_settings": {
                "defaults": {
                    "board_outline_line_width": 0.1,
                    "copper_line_width": 0.2,
                    "silk_line_width": 0.15,
                    "silk_text_size_h": 0.8,
                    "silk_text_size_v": 0.8,
                    "silk_text_thickness": 0.15,
                },
                "rules": {
                    "min_clearance": 0.15,
                    "min_connection": 0.0,
                    "min_copper_edge_clearance": 0.3,
                    "min_hole_clearance": 0.25,
                    "min_hole_to_hole": 0.25,
                    "min_microvia_diameter": 0.2,
                    "min_microvia_drill": 0.1,
                    "min_resolved_spokes": 1,
                    "min_silk_clearance": 0.0,
                    "min_text_height": 0.6,
                    "min_text_thickness": 0.08,
                    "min_through_hole_diameter": 0.3,
                    "min_track_width": 0.15,
                    "min_via_annular_width": 0.1,
                    "min_via_diameter": 0.5,
                    "solder_mask_to_copper_clearance": 0.0,
                    "use_height_for_length_calcs": True,
                },
                "rule_severities": {
                    "silk_overlap": "ignore",
                    "silk_over_copper": "ignore",
                    "silk_edge_clearance": "ignore",
                    "lib_footprint_issues": "ignore",
                    "lib_footprint_mismatch": "ignore",
                    "text_height": "ignore",
                    "text_thickness": "ignore",
                    "footprint_type_mismatch": "ignore",
                },
                "track_widths": [0.0, 0.2, 0.3, 0.5, 0.8],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                   {"diameter": 0.6, "drill": 0.3}],
            },
        },
        "meta": {"filename": C.PROJECT + ".kicad_pro", "version": 1},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.15, "track_width": 0.2,
                 "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12,
                 "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                 "diff_pair_width": 0.2, "line_style": 0,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6},
                {"name": "Power", "clearance": 0.15, "track_width": 0.5,
                 "via_diameter": 0.8, "via_drill": 0.4, "bus_width": 12,
                 "diff_pair_gap": 0.25, "diff_pair_via_gap": 0.25,
                 "diff_pair_width": 0.2, "line_style": 0,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6},
                {"name": "USB", "clearance": 0.15, "track_width": 0.25,
                 "via_diameter": 0.6, "via_drill": 0.3, "bus_width": 12,
                 "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25,
                 "diff_pair_width": 0.3, "line_style": 0,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1,
                 "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "wire_width": 6},
            ],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in C.POWER_NETS]
            + [{"netclass": "USB", "pattern": "USB_D*"}],
        },
        "pcbnew": {"last_paths": {}, "page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [],
        "text_variables": {},
    }
    with open(PRO, "w") as f:
        json.dump(pro, f, indent=2)


# ── geometry helpers ─────────────────────────────────────────────────────────
def add_line(board, layer, a, b, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pt(*a))
    s.SetEnd(pt(*b))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def add_arc(board, layer, center, start, angle_deg, width=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetCenter(pt(*center))
    s.SetStart(pt(*start))
    s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(angle_deg, pcbnew.DEGREES_T), True)
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def outline(board):
    W, H, r = C.BOARD_W, C.BOARD_H, C.CORNER_R
    e = pcbnew.Edge_Cuts
    add_line(board, e, (r, 0), (W - r, 0))
    add_line(board, e, (W, r), (W, H - r))
    add_line(board, e, (W - r, H), (r, H))
    add_line(board, e, (0, H - r), (0, r))
    add_arc(board, e, (W - r, r), (W - r, 0), 90)
    add_arc(board, e, (W - r, H - r), (W, H - r), 90)
    add_arc(board, e, (r, H - r), (r, H), 90)
    add_arc(board, e, (r, r), (0, r), 90)


def set_rect_outline(zone, x0, y0, x1, y1):
    # Build the outline in place: a temporary SHAPE_POLY_SET would be freed by
    # Python while the zone still references it.
    ol = zone.Outline()
    ol.RemoveAllContours()
    ol.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        ol.Append(mm(OX + x), mm(OY + y))


def add_keepout(board, x0, y0, x1, y1, name):
    z = pcbnew.ZONE(board)
    z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(True)
    z.SetDoNotAllowFootprints(False)
    z.SetZoneName(name)
    ls = pcbnew.LSET()
    ls.AddLayer(pcbnew.F_Cu)
    ls.AddLayer(pcbnew.B_Cu)
    z.SetLayerSet(ls)
    set_rect_outline(z, x0, y0, x1, y1)
    board.Add(z)


def add_gnd_zone(board, layer, net):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    z.SetZoneName("GND_" + ("TOP" if layer == pcbnew.F_Cu else "BOT"))
    z.SetLocalClearance(mm(0.25))
    z.SetMinThickness(mm(0.2))
    z.SetThermalReliefGap(mm(0.3))
    z.SetThermalReliefSpokeWidth(mm(0.35))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetAssignedPriority(0)
    set_rect_outline(z, 0, 0, C.BOARD_W, C.BOARD_H)
    board.Add(z)
    return z


def silk_text(board, text, x, y, size=0.8, rot=0, layer=pcbnew.F_SilkS, bold=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(0.15 if not bold else 0.2))
    t.SetTextAngleDegrees(rot)
    if bold:
        t.SetBold(True)
    if layer == pcbnew.B_SilkS:
        t.SetMirrored(True)
    board.Add(t)


def _track(board, net, layer, pts, width):
    for a, b in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(pt(*a))
        t.SetEnd(pt(*b))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        t.SetNet(net)
        t.SetLocked(True)
        board.Add(t)


def preroute_usb(board, net):
    """Hand-route the USB-C D+/D- pin pairs (0.5 mm pitch is too tight for the
    autorouter). D+ (A6/B6) joins on top in a loop around the A7 via; D- (A7/B7)
    joins on the bottom layer between two vias."""
    j = next(p for p in C.PARTS if p.ref == "J1")
    jx, jy = j.pcb[0], j.pcb[1]
    e = jx + 4.77                      # rear end of the signal pads
    yB7, yA6, yA7, yB6 = jy - 0.75, jy - 0.25, jy + 0.25, jy + 0.75
    dn, dp = net("USB_DN"), net("USB_DP")
    w = 0.2
    # D+ loop: A6 -> right, down, back left -> B6
    _track(board, dp, pcbnew.F_Cu, [(e, yA6), (e + 1.48, yA6), (e + 1.78, yA6 + 0.3),
                                     (e + 1.78, yB6), (e + 1.48, yB6 + 0.3),
                                     (e + 0.48, yB6 + 0.3), (e + 0.18, yB6), (e, yB6)], w)
    va7 = (e + 0.88, yA7 + 0.15)       # inside the D+ loop
    vb7 = (e + 2.48, yB7 + 0.3)        # right of the loop
    _track(board, dn, pcbnew.F_Cu, [(e, yA7), va7], w)
    _track(board, dn, pcbnew.F_Cu, [(e, yB7), (e + 2.18, yB7), vb7], w)
    _track(board, dn, pcbnew.B_Cu, [va7, vb7], w)
    for v in (va7, vb7):
        via = pcbnew.PCB_VIA(board)
        via.SetPosition(pt(*v))
        via.SetWidth(mm(0.6))
        via.SetDrill(mm(0.3))
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetNet(dn)
        via.SetLocked(True)
        board.Add(via)


# ── stage: place ─────────────────────────────────────────────────────────────
def stage_place():
    write_project()
    board = pcbnew.NewBoard(PCB)
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    board.SetCopperLayerCount(2)

    # Title block
    tb = board.GetTitleBlock()
    tb.SetTitle(C.TITLE)
    tb.SetRevision(C.REV)
    tb.SetCompany("x3utils-esp32")
    tb.SetComment(0, "2 Lagen, 1,6 mm, HASL/ENIG, alle Bauteile oben (JLCPCB)")

    outline(board)

    nets = {}

    def net(name):
        if name not in nets:
            n = pcbnew.NETINFO_ITEM(board, name)
            board.Add(n)
            nets[name] = n
        return nets[name]

    for p in C.PARTS:
        lib, name = p.fp.split(":")
        libdir = os.path.join(KDIR if lib == C.PROJECT else FPROOT, lib + ".pretty")
        fp = pcbnew.FootprintLoad(libdir, name)
        if fp is None:
            raise SystemExit("footprint not found: " + p.fp)
        fp.SetReference(p.ref)
        fp.SetValue(p.value)
        fp.SetFPIDAsString(p.fp)
        x, y, rot = p.pcb
        fp.SetPosition(pt(x, y))
        fp.SetOrientationDegrees(rot)
        fp.SetPath(pcbnew.KIID_PATH("/" + sym_uuid(p.ref)))
        if p.lcsc:
            fp.SetProperty("LCSC", p.lcsc)
        if not p.bom:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM
                             | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        for pad in fp.Pads():
            num = pad.GetNumber()
            if num in p.pins and p.pins[num]:
                pad.SetNet(net(p.pins[num]))
        # Reference designators go to the fab (assembly) layer; the silkscreen
        # only carries functional labels (see circuit.SILK) so it stays legible.
        ref = fp.Reference()
        ref.SetLayer(pcbnew.F_Fab)
        ref.SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
        ref.SetTextThickness(mm(0.1))
        fp.Value().SetVisible(False)
        if p.ref == "U2":
            # solid (no thermal relief) exposed pad: the charger is the hot spot
            for pad in fp.Pads():
                if pad.GetNumber() == "9":
                    pad.SetZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        board.Add(fp)

    preroute_usb(board, net)

    # KiKit tab annotations (virtual footprints, nothing gets manufactured)
    for i, (x, y, rot) in enumerate(C.PANEL_TABS):
        tab = pcbnew.FootprintLoad(os.path.join(KDIR, "kikit.pretty"), "Tab")
        tab.SetFPIDAsString("kikit:Tab")
        tab.SetReference("KT%d" % (i + 1))
        tab.SetPosition(pt(x, y))
        tab.SetOrientationDegrees(rot)
        tab.SetAttributes(tab.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM
                          | pcbnew.FP_EXCLUDE_FROM_POS_FILES | pcbnew.FP_BOARD_ONLY)
        board.Add(tab)

    for text, x, y, size, rot, side in C.SILK:
        silk_text(board, text, x, y, size, rot,
                  pcbnew.F_SilkS if side == "F" else pcbnew.B_SilkS, bold=size >= 1.0)

    # Make sure every net exists even if no pad is placed yet.
    for p in C.PARTS:
        for n in p.pins.values():
            if n:
                net(n)

    # Antenna keep-out across the whole board width above the module's
    # antenna base (module footprint carries its own, this one makes it
    # explicit for the router and for the pours).
    add_keepout(board, -1, -1, C.BOARD_W + 1, C.U1_Y - 6.75, "ANTENNA_KEEPOUT")

    pcbnew.SaveBoard(PCB, board)
    print("placed", len(C.PARTS), "parts,", len(nets), "nets ->", PCB)



# ── stage: dsn ───────────────────────────────────────────────────────────────
def stage_dsn():
    board = pcbnew.LoadBoard(PCB)
    # KiCad 7's Specctra exporter crashes on board-level zones; the antenna
    # keep-out is also carried by the module footprint, so drop zones here.
    for z in list(board.Zones()):
        board.Remove(z)
    out = os.path.join(KDIR, C.PROJECT + ".dsn")
    ok = pcbnew.ExportSpecctraDSN(board, out)
    patch_dsn(out)
    print("DSN export", ok, out)


def dsn_rect(layer, x0, y0, x1, y1):
    X = lambda v: "%.0f" % ((OX + v) * 1000)  # noqa: E731
    Y = lambda v: "%.0f" % (-(OY + v) * 1000)  # noqa: E731
    return '    (keepout "" (rect %s %s %s %s %s))\n' % (layer, X(x0), Y(y1), X(x1), Y(y0))


# Areas the router must not use (board coordinates, mm).
EPAD = (C.U1_X - 1.5, C.U1_Y + 2.46)        # module EPAD centre


def router_keepouts():
    W, H, e = C.BOARD_W, C.BOARD_H, 0.45
    k = []
    for L in ("F.Cu", "B.Cu"):
        # copper-to-edge clearance frame + rounded corners
        k += [(L, -1, -1, W + 1, e), (L, -1, H - e, W + 1, H + 1),
              (L, -1, -1, e, H + 1), (L, W - e, -1, W + 1, H + 1)]
        for cx, cy in ((0, 0), (W, 0), (0, H), (W, H)):
            k.append((L, cx - 1.3, cy - 1.3, cx + 1.3, cy + 1.3))
    # no top-layer tracks between the module pads (under the module body)
    k.append(("F.Cu", C.U1_X - 7.8, C.U1_Y - 6.75, C.U1_X + 7.8, C.U1_Y + 11.55))
    # keep the bottom layer under the EPAD / charger pad free for GND vias
    k.append(("B.Cu", EPAD[0] - 2.3, EPAD[1] - 2.3, EPAD[0] + 2.3, EPAD[1] + 2.3))
    xs = [v[0] for v in C.THERMAL_VIAS]
    ys = [v[1] for v in C.THERMAL_VIAS]
    k.append(("B.Cu", min(xs) - 0.8, min(ys) - 0.8, max(xs) + 0.8, max(ys) + 0.8))
    return k


def patch_dsn(path):
    txt = open(path).read()
    ko = "".join(dsn_rect(*k) for k in router_keepouts())
    txt = txt.replace("    (via ", ko + "    (via ", 1)
    # The EPAD reaches GND through its own vias + the pours, not through tracks.
    txt = txt.replace(" U1-41", "")
    open(path, "w").write(txt)



# ── GND via stitching ────────────────────────────────────────────────────────
def _new_via(board, net, x, y, dia=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pt(x, y))
    v.SetWidth(mm(dia))
    v.SetDrill(mm(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    board.Add(v)
    return v


def _free(board, net, x, y, r, obstacles):
    p = pt(x, y)
    for item, layer in obstacles:
        if item.GetNetCode() == net.GetNetCode():
            # same-net vias still need drill-to-drill spacing
            if isinstance(item, pcbnew.PCB_VIA):
                d = item.GetPosition() - p
                if math.hypot(d.x, d.y) < mm(1.0):
                    return False
            continue
        if item.GetEffectiveShape(layer).Collide(p, mm(r)):
            return False
    return True


def add_gnd_vias(board, net):
    """EPAD thermal vias + a stitching grid tying both GND pours together."""
    epad = 0
    for dx in (-0.9, 0.9):
        for dy in (-0.9, 0.9):
            _new_via(board, net, EPAD[0] + dx, EPAD[1] + dy)
            epad += 1
    for x, y in C.THERMAL_VIAS:
        _new_via(board, net, x, y)
        epad += 1

    obstacles = []
    for t in board.GetTracks():
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if t.IsOnLayer(L):
                obstacles.append((t, L))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pad.IsOnLayer(L):
                    obstacles.append((pad, L))
    # Holes of mechanical (unnumbered) pads also block vias.
    courtyards = []
    for fp in board.GetFootprints():
        if fp.GetReference() in ("U1",):
            continue
        cy = fp.GetCourtyard(pcbnew.F_Cu if False else pcbnew.F_CrtYd)
        if cy.OutlineCount():
            courtyards.append(cy)

    placed = 0
    W, H = C.BOARD_W, C.BOARD_H
    step = 2.5
    y = C.U1_Y - 6.75 + 1.2
    while y < H - 1.2:
        x = 1.2
        while x < W - 1.2:
            p = pt(x, y)
            # skip the module's antenna keep-out and component bodies
            inside_part = any(c.Contains(p) for c in courtyards)
            if not inside_part and _free(board, net, x, y, 0.3 + 0.2, obstacles):
                v = _new_via(board, net, x, y)
                obstacles.append((v, pcbnew.F_Cu))
                placed += 1
            x += step
        y += step
    return epad, placed


# ── stage: ses ───────────────────────────────────────────────────────────────
def import_ses(board, path):
    """Import Freerouting's session file (wires + vias) into [board]."""
    tree = sexpr.parse(open(path).read())[0]
    routes = sexpr.find(tree, "routes")
    res = sexpr.find(routes, "resolution")
    scale = {"um": 1e-3, "mm": 1.0, "mil": 0.0254}[res[1]] / float(res[2])  # -> mm
    nets = {n.GetNetname(): n for n in board.GetNetsByName().values()}
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    ntracks = nvias = 0
    for net in sexpr.find_all(sexpr.find(routes, "network_out"), "net"):
        ni = nets[str(net[1])]
        for w in sexpr.find_all(net, "wire"):
            p = sexpr.find(w, "path")
            layer, width = layers[str(p[1])], float(p[2]) * scale
            coords = [float(v) * scale for v in p[3:]]
            pts = [(coords[i], -coords[i + 1]) for i in range(0, len(coords), 2)]
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
                t.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
                t.SetWidth(mm(width))
                t.SetLayer(layer)
                t.SetNet(ni)
                board.Add(t)
                ntracks += 1
        for v in sexpr.find_all(net, "via"):
            name = str(v[1])  # Via[0-1]_800:400_um
            dia, drill = name.split("_")[1].split(":")
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(mm(float(v[2]) * scale), mm(-float(v[3]) * scale)))
            via.SetWidth(mm(float(dia) / 1000))
            via.SetDrill(mm(float(drill) / 1000))
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(ni)
            board.Add(via)
            nvias += 1
    return ntracks, nvias


def stage_ses():
    board = pcbnew.LoadBoard(PCB)
    for t in list(board.GetTracks()):
        if not t.IsLocked():
            board.Remove(t)
    nt, nv = import_ses(board, os.path.join(KDIR, C.PROJECT + ".ses"))
    print("imported %d track segments, %d vias" % (nt, nv))
    gnd = board.FindNet("GND")
    for z in list(board.Zones()):
        if not z.GetIsRuleArea():
            board.Remove(z)
    print("GND vias: %d EPAD, %d stitching" % add_gnd_vias(board, gnd))
    add_gnd_zone(board, pcbnew.F_Cu, gnd)
    add_gnd_zone(board, pcbnew.B_Cu, gnd)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    board.BuildConnectivity()
    print("unconnected:", board.GetConnectivity().GetUnconnectedCount(True))
    pcbnew.SaveBoard(PCB, board)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "place"
    globals()["stage_" + stage]()
