// X3-Tuner case — faceted "stick" style, two-part snap-fit, PCB + 1S LiPo.
//
// Design language: flat top and bottom, 45 degree facets along every edge
// (octagonal cross-section, chamfered corners in plan view), small radius on
// the plan corners, matte black. Light slits instead of visible LEDs, recessed
// pin-holes for RESET/BOOT, USB-C and the power slider on the long sides, the
// SWD port in the end face.
//
//   part = "bottom" | "lid"     single parts (STL)
//   part = "print"              both parts laid out for printing (lid upside down)
//   part = "assembly"           closed device (opaque, internals visible through the openings)
//   part = "xray"               see-through shell showing PCB and battery
//   part = "exploded"           exploded view
//   part = "section"            cutaway along the length (layer stack)
//
// All board-related positions come from board_data.scad, which
// hardware/gen/make_case_data.py generates from hardware/gen/circuit.py.
// Print: PLA/PETG (matte black looks best), 0.2 mm layers, no supports,
// bottom shell on its floor, lid with its top face on the bed.

include <board_data.scad>

part = "assembly";

/* [Battery] */
// Pocket for a 503040 LiPo (30 x 40 x 5 mm nominal, ~600 mAh) incl. margin.
BAT = [31.5, 42.0, 5.6];

/* [Shell] */
WALL = 1.6;       // side walls
FLOOR = 1.2;      // bottom thickness
LID = 1.4;        // top thickness
GAP = 0.35;       // PCB edge to inner wall
BAT_GAP = 1.5;    // battery top to PCB underside (THT tails, USB-C shell legs)
TOP_CLEAR = 5.4;  // PCB top to lid underside (tallest part: JST-PH, ~4.9 mm)
END_EXT = 7.0;    // room behind the SWD edge: header pins + battery plug
ANT_EXT = 3.0;    // extra room at the antenna end (lets the corner facets clear the PCB)
FACET = 2.5;      // 45 degree facet along the top and bottom edges
CORNER = 5.0;     // 45 degree corner facet in plan view
ROUND = 1.2;      // plan-view rounding of the facet edges
LIP_T = 0.8;      // snap lip thickness
LIP_H = 2.2;      // snap lip height
FIT = 0.15;       // print clearance lip <-> skirt
BTN_H = 1.5;      // tactile switch height (TS-1187A)
PIN_HOLE = 1.3;   // RESET/BOOT pin-hole diameter (paper clip)
SLIT = [3.8, 0.9];  // LED light slit (x, y)

$fn = 40;

Z_PCB_BOT = FLOOR + BAT[2] + BAT_GAP;
Z_PCB_TOP = Z_PCB_BOT + PCB_T;
H = Z_PCB_TOP + TOP_CLEAR + LID;
Z_SPLIT = Z_PCB_TOP;
Z_LID_IN = H - LID;
FACET_IN = FACET - 0.8;  // keeps ~1.4 mm wall across the facets

IN = [-GAP, -END_EXT, BOARD_W + GAP, BOARD_H + GAP + ANT_EXT];   // x0 y0 x1 y1
OUT = [IN[0] - WALL, IN[1] - WALL, IN[2] + WALL, IN[3] + WALL];

// ── geometry helpers ────────────────────────────────────────────────────────
module chamfer_rect(b, c) {
  polygon([[b[0] + c, b[1]], [b[2] - c, b[1]], [b[2], b[1] + c], [b[2], b[3] - c],
           [b[2] - c, b[3]], [b[0] + c, b[3]], [b[0], b[3] - c], [b[0], b[1] + c]]);
}
// Plan outline of the shell, grown/shrunk by d (negative = inside).
module plan(d = 0) {
  offset(r = ROUND) offset(delta = -ROUND) offset(delta = d) chamfer_rect(OUT, CORNER);
}
// Faceted solid: plan(d) between z0..z1 with 45 degree facets cb (bottom), ct (top).
module facet_body(d, z0, z1, cb, ct) {
  hull() {
    translate([0, 0, z0]) linear_extrude(0.01) plan(d - cb);
    translate([0, 0, z0 + cb]) linear_extrude(z1 - z0 - cb - ct) plan(d);
    translate([0, 0, z1 - 0.01]) linear_extrude(0.01) plan(d - ct);
  }
}
module shell_solid() { facet_body(0, 0, H, FACET, FACET); }
module cavity() { facet_body(-WALL, FLOOR, Z_LID_IN, FACET_IN, FACET_IN); }

module rbox(c, s, r) {  // centred rounded box
  translate(c) hull() for (x = [-s[0] / 2 + r, s[0] / 2 - r], y = [-s[1] / 2 + r, s[1] / 2 - r])
    translate([x, y, -s[2] / 2]) cylinder(r = r, h = s[2]);
}

// ── openings through the shell ──────────────────────────────────────────────
module ports() {
  // USB-C on whichever long side the board puts it
  usb_out = USB_RIGHT ? OUT[2] : OUT[0];
  translate([usb_out, USB_Y, Z_PCB_TOP + 1.63]) rotate([0, USB_RIGHT ? -90 : 90, 0]) {
    rbox([0, 0, (WALL + 1.2) / 2 - 1], [3.9, 9.7, WALL + 1.2 + 1], 1.5);
    rbox([0, 0, 0.1], [5.0, 10.8, 1.2], 2.0);  // soft lead-in on the outside
  }
  // power slider: slot + finger scoop
  sw_out = SW1_RIGHT ? OUT[2] : OUT[0];
  dir = SW1_RIGHT ? 1 : -1;
  translate([SW1_RIGHT ? IN[2] - 0.5 : OUT[0] - 1, SW1_Y - 3.6, Z_PCB_TOP - 0.4])
    cube([WALL + 1.5, 7.2, 3.0]);
  translate([sw_out + dir * 2.4, SW1_Y, Z_PCB_TOP + 1.1]) scale([1, 1.7, 1]) sphere(r = 3.4);
  // SWD port in the end face: a 5-pin Dupont housing slides over the pins
  pins_c = J3_PIN1_X - 2 * J3_PITCH;
  translate([pins_c, OUT[1] - 1, Z_PCB_TOP + 1.27]) rotate([-90, 0, 0]) {
    rbox([0, 0, (WALL + 1.2) / 2], [13.7, 3.4, WALL + 1.2 + 1], 0.6);
    rbox([0, 0, 0.8], [15.0, 4.6, 1.6], 1.2);
  }
}

// engraving depth on visible faces
ENGRAVE = 0.45;
// The cut-outs reach from `from` (mm under the surface) out through the face;
// the previews reuse them with a thin depth as a light "ink" in the engraving.
module end_face_labels(from = ENGRAVE - 0.01, depth = ENGRAVE + 1) {  // pin names under the SWD slot
  for (i = [0:4]) translate([J3_PIN1_X - i * J3_PITCH, OUT[1] + from, Z_PCB_TOP - 2.3])
    rotate([90, 0, 0]) linear_extrude(depth) rotate(90)
      text(J3_LABELS[i], size = 1.7, font = "Liberation Sans:style=Bold", halign = "right", valign = "center");
}
module bottom_logo(from = ENGRAVE - 0.01, depth = ENGRAVE) {  // readable when the device is turned over
  translate([BOARD_W / 2, (IN[1] + IN[3]) / 2, from - depth]) linear_extrude(depth) mirror([1, 0, 0]) {
    translate([0, 3]) text("X3·TUNER", size = 4.2, font = "Liberation Sans:style=Bold",
                          halign = "center", valign = "center", spacing = 1.15);
    translate([0, -3.5]) text("SWD · x3utils-esp32", size = 2.0, font = "Liberation Sans",
                             halign = "center", valign = "center");
  }
}
module engraving_ink() { color("#a9aeb6") { end_face_labels(ENGRAVE - 0.01, 0.15); bottom_logo(ENGRAVE - 0.01, 0.15); } }

// ── bottom shell ────────────────────────────────────────────────────────────
module lip_ring(extra = 0) { difference() { plan(-WALL + LIP_T + extra); plan(-WALL); } }
SNAPS = [[IN[0], 12], [IN[0], 44], [IN[2], 12], [IN[2], 44]];
module snap(s, grow = 0) {  // wedge bump on the lip; grow > 0 = matching groove
  dir = s[0] < 1 ? -1 : 1;
  x0 = s[0] + dir * (LIP_T - 0.1);
  z = Z_SPLIT + LIP_H / 2;
  hull() {
    translate([min(x0, x0 + dir * 0.01), s[1] - 2.5 - grow, z - 0.6 - grow]) cube([0.01, 5 + 2 * grow, 1.2 + 2 * grow]);
    translate([x0 + dir * (0.55 + grow) - 0.005, s[1] - 2.5 - grow, z - 0.05 - grow / 2]) cube([0.01, 5 + 2 * grow, 0.1 + grow]);
  }
}

module bottom() {
  intersection() {
    shell_solid();  // everything stays inside the faceted envelope
    difference() {
      union() {
        intersection() {
          shell_solid();
          translate([OUT[0] - 1, OUT[1] - 1, -1]) cube([OUT[2] - OUT[0] + 2, OUT[3] - OUT[1] + 2, Z_SPLIT + 1]);
        }
        translate([0, 0, Z_SPLIT - 0.01]) linear_extrude(LIP_H) lip_ring();
        for (s = SNAPS) snap(s);
        // PCB supports: side strips, antenna-end strip, two blocks at the port end
        for (b = [[IN[0] - 0.3, 0.5, 1.0, BOARD_H - 0.5], [BOARD_W - 1.0, 0.5, IN[2] + 0.3, BOARD_H - 0.5],
                  [0.5, BOARD_H - 1.2, BOARD_W - 0.5, BOARD_H + 0.3], [12, 0, 18, 1.2], [34, 0, 37.5, 1.2]])
          translate([b[0], b[1], FLOOR - 0.5]) cube([b[2] - b[0], b[3] - b[1], Z_PCB_BOT - FLOOR + 0.5]);
        // battery fences
        bx0 = (BOARD_W - BAT[0]) / 2;
        by0 = BOARD_H - 2.5 - BAT[1];
        for (f = [[bx0 - 1.2, by0, 1.2, BAT[1]], [bx0 + BAT[0], by0, 1.2, BAT[1]],
                  [bx0 + 6, by0 - 1.2, 6, 1.2], [bx0 + BAT[0] - 12, by0 - 1.2, 6, 1.2]])
          translate([f[0], f[1], FLOOR - 0.5]) cube([f[2], f[3], 2.5]);
      }
      cavity_minus_supports();
      ports();
      end_face_labels();
      bottom_logo();
    }
  }
}
// The cavity is cut first, then supports/fences are added back on top of it.
module cavity_minus_supports() {
  difference() {
    cavity();
    for (b = [[IN[0] - 0.3, 0.5, 1.0, BOARD_H - 0.5], [BOARD_W - 1.0, 0.5, IN[2] + 0.3, BOARD_H - 0.5],
              [0.5, BOARD_H - 1.2, BOARD_W - 0.5, BOARD_H + 0.3], [12, 0, 18, 1.2], [34, 0, 37.5, 1.2]])
      translate([b[0], b[1], FLOOR - 0.6]) cube([b[2] - b[0], b[3] - b[1], Z_PCB_BOT - FLOOR + 0.6]);
    bx0 = (BOARD_W - BAT[0]) / 2;
    by0 = BOARD_H - 2.5 - BAT[1];
    for (f = [[bx0 - 1.2, by0, 1.2, BAT[1]], [bx0 + BAT[0], by0, 1.2, BAT[1]],
              [bx0 + 6, by0 - 1.2, 6, 1.2], [bx0 + BAT[0] - 12, by0 - 1.2, 6, 1.2]])
      translate([f[0], f[1], FLOOR - 0.6]) cube([f[2], f[3], 2.6]);
  }
}

// ── lid ─────────────────────────────────────────────────────────────────────
module pin_guide(c) {  // tube that guides a paper clip onto the tactile switch
  translate([c[0], c[1], Z_PCB_TOP + BTN_H + 0.6])
    cylinder(d = PIN_HOLE + 1.8, h = Z_LID_IN - (Z_PCB_TOP + BTN_H + 0.6) + 0.01);
}
module light_tube(c) {  // baffle around a LED so the slit glows cleanly
  s = [SLIT[0] + 0.6, 2.4];
  translate([c[0] - s[0] / 2 - 0.8, c[1] - s[1] / 2 - 0.8, Z_PCB_TOP + 1.0])
    difference() {
      cube([s[0] + 1.6, s[1] + 1.6, Z_LID_IN - Z_PCB_TOP - 1.0 + 0.01]);
      translate([0.8, 0.8, -1]) cube([s[0], s[1], 20]);
    }
}

module lid() {
  intersection() {
    shell_solid();
    difference() {
      union() {
        difference() {
          intersection() {
            shell_solid();
            translate([OUT[0] - 1, OUT[1] - 1, Z_SPLIT]) cube([OUT[2] - OUT[0] + 2, OUT[3] - OUT[1] + 2, H]);
          }
          cavity();
          translate([0, 0, Z_SPLIT - 0.01]) linear_extrude(LIP_H + FIT) lip_ring(FIT);
          for (s = SNAPS) snap(s, 0.15);
        }
        for (p = LID_POSTS) translate([p[0], p[1], Z_PCB_TOP + 0.1]) cylinder(d = 2.0, h = Z_LID_IN - Z_PCB_TOP);
        for (c = [LED_STAT_XY, LED_CHG_XY]) light_tube(c);
        for (c = [SW2_XY, SW3_XY]) pin_guide(c);
      }
      // light slits (open, flush) and pin-holes for RESET / BOOT
      for (c = [LED_STAT_XY, LED_CHG_XY])
        translate([c[0] - SLIT[0] / 2, c[1] - SLIT[1] / 2, Z_PCB_TOP]) cube([SLIT[0], SLIT[1], H]);
      for (c = [SW2_XY, SW3_XY]) translate([c[0], c[1], Z_PCB_TOP]) {
        cylinder(d = PIN_HOLE, h = H);
        translate([0, 0, H - Z_PCB_TOP - 0.5]) cylinder(d1 = PIN_HOLE, d2 = PIN_HOLE + 1.0, h = 0.51);
      }
      ports();
      end_face_labels();
    }
  }
}

// ── simplified board + battery for previews ─────────────────────────────────
// Small parts come from PARTS (real footprint positions from the routed board),
// connectors, switches and the module are modelled here.
module wire(pts, d = 1.0) {  // flexible lead as a chain of rounded segments
  for (i = [0:len(pts) - 2]) hull() { translate(pts[i]) sphere(d = d, $fn = 12); translate(pts[i + 1]) sphere(d = d, $fn = 12); }
}
module pcb_board() {
  translate([0, 0, Z_PCB_BOT]) linear_extrude(PCB_T) offset(r = BOARD_R) offset(delta = -BOARD_R) square([BOARD_W, BOARD_H]);
}
module module_pcb() { translate([U1_XY[0] - 9, MODULE_BOTTOM_Y, Z_PCB_TOP]) cube([18, ANTENNA_Y - MODULE_BOTTOM_Y + 6, 0.8]); }
module j3_housing() { translate([J3_PIN1_X - 4 * J3_PITCH - 1.27, J3_ROW_Y - 4.04, Z_PCB_TOP]) cube([12.7, 2.54, 2.5]); }
module module_can() {
  translate([U1_XY[0] - 8.6, MODULE_BOTTOM_Y + 0.4, Z_PCB_TOP + 0.8]) cube([17.2, ANTENNA_Y - MODULE_BOTTOM_Y - 0.8, 2.4]);
}
module pcb_model() {
  t = Z_PCB_TOP;
  color("#1f6f43") pcb_board();
  for (p = PARTS) color(p[5]) translate([p[0], p[1], t]) cube([p[2], p[3], p[4]]);
  // ESP32-C3-WROOM-02: module PCB, shield can, meander antenna
  mx = U1_XY[0] - 9;
  color("#222") module_pcb();
  color("#c9ccd1") module_can();
  color("#555") translate([U1_XY[0], (MODULE_BOTTOM_Y + ANTENNA_Y) / 2, t + 3.2]) linear_extrude(0.05) {
    translate([0, 1.2]) text("ESP32-C3", size = 2.0, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
    translate([0, -1.8]) text("WROOM-02", size = 1.3, halign = "center", valign = "center", font = "Liberation Sans");
  }
  color("#c8a24a") translate([mx + 2, ANTENNA_Y + 1, t + 0.8]) {
    for (i = [0:6]) translate([i * 2, 0, 0]) cube([0.4, 3.6, 0.04]);
    for (i = [0:5]) translate([i * 2, (i % 2) * 3.2, 0]) cube([2.4, 0.4, 0.04]);
  }
  // USB-C receptacle (opening faces the board edge)
  ux = USB_RIGHT ? USB_FRONT_X - 7.3 : USB_FRONT_X;
  color("#d0d3d8") translate([ux, USB_Y, t + 1.63]) rotate([0, 90, 0]) hull()
    for (y = [-2.87, 2.87]) translate([0, y, 0]) cylinder(r = 1.6, h = 7.3, $fn = 24);
  color("#111") translate([USB_RIGHT ? USB_FRONT_X - 0.6 : USB_FRONT_X - 0.01, USB_Y, t + 1.63]) rotate([0, 90, 0]) hull()
    for (y = [-2.9, 2.9]) translate([0, y, 0]) cylinder(r = 1.1, h = 0.61, $fn = 20);
  // JST-PH battery socket + plug
  color("#efe8d8") translate([J2_XY[0] - 3.95, J2_FRONT_Y, t]) cube([7.9, 6.0, 4.9]);
  color("#f7f4ee") translate([J2_XY[0] - 3.0, J2_FRONT_Y - 5.0, t + 0.6]) cube([6.0, 5.0, 3.4]);
  // right-angle 5-pin SWD header
  color("#111") j3_housing();
  for (i = [0:4]) color("gold") translate([J3_PIN1_X - i * J3_PITCH - 0.32, J3_TIP_Y, t + 0.95])
    cube([0.64, J3_ROW_Y - J3_TIP_Y, 0.64]);
  // slide switch with lever
  sw_body_x = SW1_RIGHT ? BOARD_W - 3.2 : 0.35;
  color("#2a2a2a") translate([sw_body_x, SW1_Y - 3.35, t]) cube([2.85, 6.7, 1.4]);
  color("#bbb") translate([sw_body_x, SW1_Y - 3.35, t + 1.4]) cube([2.85, 6.7, 0.1]);
  color("#555") translate([SW1_RIGHT ? BOARD_W - 0.1 : SW1_LEVER_X, SW1_Y - 0.75, t + 0.2])
    cube([abs(SW1_LEVER_X - (SW1_RIGHT ? BOARD_W - 0.1 : 0.45)), 1.5, 1.0]);
  // RESET / BOOT tactile switches
  for (c = [SW2_XY, SW3_XY]) translate([c[0], c[1], t]) {
    color("#2a2a2a") translate([-2.55, -2.55, 0]) cube([5.1, 5.1, 0.8]);
    color("#c0c4ca") translate([-2.55, -2.55, 0.8]) cube([5.1, 5.1, 0.15]);
    color("#1a1a1a") cylinder(d = 2.6, h = BTN_H);
  }
}
BAT_XY = [(BOARD_W - BAT[0]) / 2, BOARD_H - 2.5 - BAT[1]];
BAT_BODY = [BAT[0] - 0.6, BAT[1] - 0.6, 5.0];
module battery_body(at = false) {
  b = BAT_BODY;
  translate(at ? [BAT_XY[0] + 0.3, BAT_XY[1] + 0.3, FLOOR + 0.05] : [0, 0, 0])
    hull() for (x = [1, b[0] - 1], y = [3, b[1] - 1], z = [1, b[2] - 1]) translate([x, y, z]) sphere(r = 1, $fn = 16);
}
module battery_model() {
  b = BAT_BODY;
  translate([BAT_XY[0] + 0.3, BAT_XY[1] + 0.3, FLOOR + 0.05]) {
    color("#b9c0c8") battery_body();
    color("#b9c0c8") translate([2, 0, b[2] / 2 - 0.2]) cube([b[0] - 4, 3, 0.4]);  // sealed tab edge
    color("#2f5fa8") translate([1.5, 5, -0.01]) cube([b[0] - 3, b[1] - 8, 0.05]);
    color("white") translate([b[0] / 2, b[1] / 2 + 2, -0.03]) mirror([1, 0, 0]) linear_extrude(0.03) {
      text("LiPo 503040", size = 2.6, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
      translate([0, -4]) text("3,7 V  600 mAh", size = 1.9, halign = "center", valign = "center", font = "Liberation Sans");
    }
  }
  // leads from the cell tab to the JST plug: along the floor, up past the board edge, into the plug
  zb = FLOOR + 2.6;
  zp = Z_PCB_TOP + 2.3;
  for (w = [[J2_XY[0] - 1, BAT_XY[0] + 4, "#d22"], [J2_XY[0] + 1, BAT_XY[0] + 5.4, "#111"]])
    color(w[2]) wire([[w[1], BAT_XY[1] + 1, zb], [w[1], BAT_XY[1] - 2, zb], [w[0], -2.5, zb], [w[0], -5.6, zb + 0.6],
                      [w[0], -6.0, zb + 2.5], [w[0], -6.0, zp - 1], [w[0], -5.6, zp], [w[0], J2_FRONT_Y - 5.0, zp]]);
}

// cutaway: keeps x < CUT_X (between two SWD pins) and paints the cut faces
CUT_X = 25.2;
module cut() { intersection() { children(); translate([OUT[0] - 5, OUT[1] - 5, -5]) cube([CUT_X - OUT[0] + 5, 100, 40]); } }
module cut_face(c) {  // the section of the children in the plane x = CUT_X, as a thin coloured plate
  color(c) translate([CUT_X, 0, 0]) rotate([0, 90, 0]) linear_extrude(0.08, center = true)
    projection(cut = true) rotate([0, -90, 0]) translate([-CUT_X, 0, 0]) children();
}

// Previews can use the finished STLs (make_case.sh writes them first): faster,
// and see-through renders blend cleanly without OpenSCAD's CSG artefacts.
USE_STL = false;
module shell(which) {
  if (USE_STL) import(str("stl/x3tuner-case-", which, ".stl"), convexity = 10);
  else if (which == "bottom") bottom();
  else lid();
}

SHELL = "#454850";
if (part == "bottom") bottom();
else if (part == "lid") lid();
else if (part == "print") {
  bottom();
  translate([OUT[2] - OUT[0] + 6, 0, H]) mirror([0, 0, 1]) lid();
} else if (part == "exploded") {
  color(SHELL) shell("bottom");
  translate([0, 0, 2]) battery_model();
  translate([0, 0, 12]) pcb_model();
  translate([0, 0, 30]) color(SHELL) shell("lid");
} else if (part == "section") {
  cut() { color(SHELL) shell("bottom"); color(SHELL) shell("lid"); pcb_model(); battery_model(); }
  cut_face("#ffb04a") { shell("bottom"); shell("lid"); }
  cut_face("#2e9b5f") pcb_board();
  cut_face("#e3e6ea") module_can();
  cut_face("#3a3a3a") { module_pcb(); j3_housing(); }
  cut_face("#cfd6de") battery_body(true);
} else if (part == "xray") {
  pcb_model();
  battery_model();
  color("#7f8794", 0.16) shell("bottom");
  color("#7f8794", 0.16) shell("lid");
} else {  // assembly: closed device; the internals show through the openings
  color(SHELL) shell("bottom");
  color(SHELL) shell("lid");
  engraving_ink();
  pcb_model();
  battery_model();
}
echo(CASE_SIZE = [OUT[2] - OUT[0], OUT[3] - OUT[1], H], CASE_CENTER = [(OUT[0] + OUT[2]) / 2, (OUT[1] + OUT[3]) / 2, H / 2]);
