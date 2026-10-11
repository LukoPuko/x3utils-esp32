// X3 case core — faceted "stick" style, two-part snap-fit, PCB + 1S LiPo.
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
// Shared by every board: a small wrapper per board (hardware/case/x3tuner_case.scad,
// hardware/carrier/case/x3mini_case.scad) sets `part`, includes its
// board_data.scad, which hardware/gen/make_case_data.py writes from the board's
// circuit file, and then this file. Board-specific overrides are the optional
// CASE_* / USB_DZ / SUPERMINI variables in board_data.scad; without them the
// X3-Tuner values apply.
// Print: PLA/PETG (matte black looks best), 0.2 mm layers, no supports,
// bottom shell on its floor, lid with its top face on the bed.

/* [Battery] */
// Pocket for a 503040 LiPo (30 x 40 x 5 mm nominal, ~600 mAh) incl. margin.
// With CASE_BAT_LID = [x0, y0] the battery instead sits in a pocket under the
// lid (taped to it) above the board; BAT is then [width, length, thickness].
BAT = is_undef(CASE_BAT) ? [31.5, 42.0, 5.6] : CASE_BAT;
BAT_IN_LID = !is_undef(CASE_BAT_LID);

/* [Shell] */
WALL = 1.6;       // side walls
FLOOR = 1.2;      // bottom thickness
LID = 1.4;        // top thickness
GAP = 0.35;       // PCB edge to inner wall
BAT_GAP = is_undef(CASE_BAT_GAP) ? 1.5 : CASE_BAT_GAP;        // battery top to PCB underside (THT tails)
TOP_CLEAR = is_undef(CASE_TOP_CLEAR) ? 5.4 : CASE_TOP_CLEAR;  // PCB top to lid underside (tallest part)
END_EXT = 7.0;    // room behind the SWD edge: header pins + battery plug
ANT_EXT = is_undef(CASE_ANT_EXT) ? 3.0 : CASE_ANT_EXT;  // extra room at the far end (corner facets / USB-C)
FACET = 2.5;      // 45 degree facet along the top and bottom edges
CORNER = is_undef(CASE_CORNER) ? 5.0 : CASE_CORNER;  // 45 degree corner facet in plan view
ROUND = 1.2;      // plan-view rounding of the facet edges
LIP_T = 0.8;      // snap lip thickness
LIP_H = 2.2;      // snap lip height
FIT = 0.15;       // print clearance lip <-> skirt
BTN_H = 1.5;      // tactile switch height (TS-1187A)
PIN_HOLE = 1.3;   // RESET/BOOT pin-hole diameter (paper clip)
SLIT = [3.8, 0.9];  // LED light slit (x, y)

$fn = 40;

Z_PCB_BOT = FLOOR + (BAT_IN_LID ? 0 : BAT[2]) + BAT_GAP;
Z_PCB_TOP = Z_PCB_BOT + PCB_T;
H = Z_PCB_TOP + TOP_CLEAR + LID;
Z_SPLIT = Z_PCB_TOP;
Z_LID_IN = H - LID;
FACET_IN = is_undef(CASE_FACET_IN) ? FACET - 0.8 : CASE_FACET_IN;  // inner facet (FACET - 0.8 keeps ~1.4 mm wall)
USB_Z = is_undef(USB_DZ) ? 1.63 : USB_DZ;                 // USB-C centre above the PCB top
USB_ROOM = is_undef(CASE_USB_ROOM) ? 0 : CASE_USB_ROOM;   // extra room on the USB side
SNAP_Y = is_undef(CASE_SNAP_Y) ? [12, 44] : CASE_SNAP_Y;  // snap positions along the long sides
LED_SLITS = is_undef(CASE_LED_SLITS) ? [LED_STAT_XY, LED_CHG_XY] : CASE_LED_SLITS;
PIN_BUTTONS = is_undef(CASE_PIN_BUTTONS) ? [SW2_XY, SW3_XY] : CASE_PIN_BUTTONS;
WINDOWS = is_undef(CASE_WINDOWS) ? [] : CASE_WINDOWS;     // [x0, y0, x1, y1] openings in the lid
LID_BLOCKS = is_undef(CASE_LID_BLOCKS) ? [] : CASE_LID_BLOCKS;  // see lid()
USB_HOLE = is_undef(CASE_USB_HOLE) ? [3.9, 9.7] : CASE_USB_HOLE;  // USB-C opening height x width
// recess for the cable's overmould around the USB-C opening: height, width, depth into the wall
USB_LEADIN = is_undef(CASE_USB_LEADIN) ? [USB_HOLE[0] + 1.1, USB_HOLE[1] + 1.1, 0.7] : CASE_USB_LEADIN;
POST_D = is_undef(CASE_POST_D) ? 2.0 : CASE_POST_D;       // lid posts pressing the PCB down
LOGO_SUB = is_undef(CASE_LOGO_SUB) ? "SWD · x3utils-esp32" : CASE_LOGO_SUB;
LOGO_ROT = is_undef(CASE_LOGO_ROT) ? 0 : CASE_LOGO_ROT;   // 90: logo along the length (narrow cases)
LABELS_UP = is_undef(CASE_LABELS_UP) ? false : CASE_LABELS_UP;  // SWD pin names above the slot
USB_END = is_undef(CASE_USB_END) ? false : CASE_USB_END;  // USB-C in the far end face (at USB_X)
// x ranges of the PCB support blocks at the SWD edge (clear of the header pins)
PORT_BLOCKS = is_undef(CASE_PORT_BLOCKS) ? [[12, 18], [34, 37.5]] : CASE_PORT_BLOCKS;
J2_D = is_undef(J2_DIR) ? -1 : J2_DIR;   // battery socket opening: -1 = towards -Y, 1 = +Y
CUT_X = is_undef(CASE_CUT_X) ? 25.2 : CASE_CUT_X;          // section plane (between two SWD pins)
STL_BASE = is_undef(STL_PREFIX) ? "stl/x3tuner-case-" : STL_PREFIX;

IN = [-GAP - (USB_RIGHT ? 0 : USB_ROOM), -END_EXT, BOARD_W + GAP + (USB_RIGHT ? USB_ROOM : 0),
      BOARD_H + GAP + ANT_EXT];   // x0 y0 x1 y1
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
  // USB-C on whichever long side the board puts it, or in the far end face
  // (local frame: x = height, y = width, z = into the case)
  usb_out = USB_RIGHT ? OUT[2] : OUT[0];
  if (USB_END) translate([USB_X, OUT[3], Z_PCB_TOP + USB_Z]) rotate([90, 0, 0]) rotate([0, 0, 90]) usb_cut();
  else translate([usb_out, USB_Y, Z_PCB_TOP + USB_Z]) rotate([0, USB_RIGHT ? -90 : 90, 0]) usb_cut();
  module usb_cut() {
    rbox([0, 0, (WALL + 1.2) / 2 - 1], [USB_HOLE[0], USB_HOLE[1], WALL + 1.2 + 1], 1.5);
    // soft lead-in on the outside, starting 0.5 mm in front of the wall
    if (is_undef(CASE_USB_LEADIN)) rbox([0, 0, 0.1], [USB_LEADIN[0], USB_LEADIN[1], 1.2], 2.0);
    else rbox([0, 0, USB_LEADIN[2] / 2 - 0.25], [USB_LEADIN[0], USB_LEADIN[1], USB_LEADIN[2] + 0.5], 2.0);
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
  for (i = [0:4]) translate([J3_PIN1_X - i * J3_PITCH, OUT[1] + from, Z_PCB_TOP + (LABELS_UP ? 4.9 : -2.3)])
    rotate([90, 0, 0]) linear_extrude(depth) rotate(90)
      text(J3_LABELS[i], size = 1.7, font = "Liberation Sans:style=Bold", halign = LABELS_UP ? "left" : "right",
           valign = "center");
}
module bottom_logo(from = ENGRAVE - 0.01, depth = ENGRAVE) {  // readable when the device is turned over
  translate([BOARD_W / 2, (IN[1] + IN[3]) / 2, from - depth]) linear_extrude(depth) mirror([1, 0, 0]) rotate(LOGO_ROT) {
    translate([0, 3]) text("X3·TUNER", size = 4.2, font = "Liberation Sans:style=Bold",
                          halign = "center", valign = "center", spacing = 1.15);
    translate([0, -3.5]) text(LOGO_SUB, size = 2.0, font = "Liberation Sans",
                             halign = "center", valign = "center");
  }
}
module engraving_ink() { color("#a9aeb6") { end_face_labels(ENGRAVE - 0.01, 0.15); bottom_logo(ENGRAVE - 0.01, 0.15); } }

// ── bottom shell ────────────────────────────────────────────────────────────
module lip_ring(extra = 0) { difference() { plan(-WALL + LIP_T + extra); plan(-WALL); } }
SNAPS = [for (x = [IN[0], IN[2]]) for (y = SNAP_Y) [x, y]];
module snap(s, grow = 0) {  // wedge bump on the lip; grow > 0 = matching groove
  dir = s[0] < 1 ? -1 : 1;
  x0 = s[0] + dir * (LIP_T - 0.1);
  z = Z_SPLIT + LIP_H / 2;
  hull() {
    translate([min(x0, x0 + dir * 0.01), s[1] - 2.5 - grow, z - 0.6 - grow]) cube([0.01, 5 + 2 * grow, 1.2 + 2 * grow]);
    translate([x0 + dir * (0.55 + grow) - 0.005, s[1] - 2.5 - grow, z - 0.05 - grow / 2]) cube([0.01, 5 + 2 * grow, 0.1 + grow]);
  }
}

// PCB supports: side strips, far-end strip, blocks at the port end
SUPPORTS = concat([[IN[0] - 0.3, 0.5, 1.0, BOARD_H - 0.5], [BOARD_W - 1.0, 0.5, IN[2] + 0.3, BOARD_H - 0.5],
                   [0.5, BOARD_H - 1.2, BOARD_W - 0.5, BOARD_H + 0.3]],
                  [for (p = PORT_BLOCKS) [p[0], 0, p[1], 1.2]]);
// fences around the battery on the floor [x, y, w, l] (battery under the board only)
BX0 = (BOARD_W - BAT[0]) / 2;
BY0 = BOARD_H - 2.5 - BAT[1];
FENCES = BAT_IN_LID ? [] : [[BX0 - 1.2, BY0, 1.2, BAT[1]], [BX0 + BAT[0], BY0, 1.2, BAT[1]],
                            [BX0 + 6, BY0 - 1.2, 6, 1.2], [BX0 + BAT[0] - 12, BY0 - 1.2, 6, 1.2]];

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
        for (b = SUPPORTS)
          translate([b[0], b[1], FLOOR - 0.5]) cube([b[2] - b[0], b[3] - b[1], Z_PCB_BOT - FLOOR + 0.5]);
        // battery fences
        for (f = FENCES) translate([f[0], f[1], FLOOR - 0.5]) cube([f[2], f[3], 2.5]);
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
    for (b = SUPPORTS)
      translate([b[0], b[1], FLOOR - 0.6]) cube([b[2] - b[0], b[3] - b[1], Z_PCB_BOT - FLOOR + 0.6]);
    for (f = FENCES) translate([f[0], f[1], FLOOR - 0.6]) cube([f[2], f[3], 2.6]);
  }
}

// ── lid ─────────────────────────────────────────────────────────────────────
module pin_guide(c) {  // tube that guides a paper clip onto the tactile switch
  translate([c[0], c[1], Z_PCB_TOP + BTN_H + 0.6])
    cylinder(d = PIN_HOLE + 1.8, h = Z_LID_IN - (Z_PCB_TOP + BTN_H + 0.6) + 0.01);
}
module light_tube(c) {  // baffle around a LED so the slit glows cleanly; c[2] = bottom above the PCB
  s = [SLIT[0] + 0.6, 2.4];
  z0 = len(c) > 2 ? c[2] : 1.0;
  translate([c[0] - s[0] / 2 - 0.8, c[1] - s[1] / 2 - 0.8, Z_PCB_TOP + z0])
    difference() {
      cube([s[0] + 1.6, s[1] + 1.6, Z_LID_IN - Z_PCB_TOP - z0 + 0.01]);
      translate([0.8, 0.8, -1]) cube([s[0], s[1], 20]);
    }
}

// opening through the lid with rounded corners and a 0.6 mm chamfer on top
module window_cut(w) {
  module r(d) { offset(r = 1.2 + d) offset(delta = -1.2) translate([w[0], w[1]]) square([w[2] - w[0], w[3] - w[1]]); }
  translate([0, 0, Z_LID_IN - 1]) linear_extrude(LID + 2) r(0);
  hull() {
    translate([0, 0, H - 0.6]) linear_extrude(0.01) r(0);
    translate([0, 0, H]) linear_extrude(0.01) r(0.6);
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
        for (p = LID_POSTS) translate([p[0], p[1], Z_PCB_TOP + 0.1]) cylinder(d = POST_D, h = Z_LID_IN - Z_PCB_TOP);
        for (c = LED_SLITS) light_tube(c);
        for (c = PIN_BUTTONS) pin_guide(c);
        // ribs / stops hanging from the lid: [x0, y0, x1, y1, bottom above the PCB top]
        for (b = LID_BLOCKS) translate([b[0], b[1], Z_PCB_TOP + b[4]]) cube([b[2] - b[0], b[3] - b[1], Z_LID_IN - Z_PCB_TOP - b[4] + 0.01]);
      }
      // light slits (open, flush), pin-holes for RESET / BOOT, service windows
      for (c = LED_SLITS)
        translate([c[0] - SLIT[0] / 2, c[1] - SLIT[1] / 2, Z_PCB_TOP]) cube([SLIT[0], SLIT[1], H]);
      for (w = WINDOWS) window_cut(w);
      for (c = PIN_BUTTONS) translate([c[0], c[1], Z_PCB_TOP]) {
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
  if (is_undef(SUPERMINI)) tuner_parts(); else supermini_model();
  // JST-PH battery socket + plug (opening towards -Y, or +Y with J2_DIR = 1)
  color("#efe8d8") translate([J2_XY[0] - 3.95, J2_FRONT_Y - (J2_D > 0 ? 6.0 : 0), t]) cube([7.9, 6.0, 4.9]);
  color("#f7f4ee") translate([J2_XY[0] - 3.0, J2_FRONT_Y - (J2_D > 0 ? 0 : 5.0), t + 0.6]) cube([6.0, 5.0, 3.4]);
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
}
// X3-Tuner: WROOM module, USB-C and the two tactile switches on the board itself
module tuner_parts() {
  t = Z_PCB_TOP;
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
  // RESET / BOOT tactile switches
  for (c = [SW2_XY, SW3_XY]) translate([c[0], c[1], t]) {
    color("#2a2a2a") translate([-2.55, -2.55, 0]) cube([5.1, 5.1, 0.8]);
    color("#c0c4ca") translate([-2.55, -2.55, 0.8]) cube([5.1, 5.1, 0.15]);
    color("#1a1a1a") cylinder(d = 2.6, h = BTN_H);
  }
}
// ESP32-C3 SuperMini on its sockets (X3-Tuner Mini carrier). SUPERMINI =
// [x, y of the USB-C edge centre, direction of USB-C (deg, 0 = +X), length,
//  width, PCB underside above carrier top, PCB thickness, pin 1 from the USB
//  edge, pin row offset from the centre line, USB-C overhang].
// Local frame (sm_frame): USB-C towards +x, the board from x = -length to 0,
// the 5V row at +y (seen from the top with USB-C up: left).
function sm(i) = SUPERMINI[i];
SM_Z = is_undef(SUPERMINI) ? 0 : Z_PCB_TOP + sm(5);   // SuperMini PCB underside
module sm_frame() { translate([sm(0), sm(1), 0]) rotate(sm(2)) children(); }
module sm_pcb() { sm_frame() translate([-sm(3), -sm(4) / 2, SM_Z]) cube([sm(3), sm(4), sm(6)]); }
module sm_rows(h, z) {  // footprint of both pin rows (socket / male header body)
  sm_frame() for (y = [sm(8), -sm(8)]) translate([-sm(7) - 7 * 2.54 - 1.27, y - 1.27, z]) cube([8 * 2.54, 2.54, h]);
}
module supermini_model() {
  t = Z_PCB_TOP;
  top = SM_Z + sm(6);
  color("#151515") sm_rows(8.5, t);                  // 2 x 1x8 sockets on the carrier
  color("#262626") sm_rows(sm(5) - 8.5, t + 8.5);    // plastic of the SuperMini's pin headers
  color("#1d3d7a") sm_pcb();
  sm_frame() {
    for (y = [sm(8), -sm(8)], i = [0:7])            // header pin tips with solder
      color("#c9c9c9") translate([-sm(7) - i * 2.54, y, top]) cylinder(d1 = 1.4, d2 = 0.7, h = 2.0, $fn = 10);
    color("#1a1a1a") translate([-13, 0, top]) rotate(45) translate([-2.5, -2.5, 0]) cube([5, 5, 0.9]);  // ESP32-C3
    color("#e8dcc0") translate([-sm(3) + 0.6, -1.6, top]) cube([1.6, 3.2, 1.0]);  // chip antenna
    color("#d0d3d8") translate([sm(9) - 7.35, 0, top + 1.63]) rotate([0, 90, 0]) hull()
      for (y = [-2.87, 2.87]) translate([0, y, 0]) cylinder(r = 1.63, h = 7.35, $fn = 24);
    color("#111") translate([sm(9) - 0.6, 0, top + 1.63]) rotate([0, 90, 0]) hull()
      for (y = [-2.9, 2.9]) translate([0, y, 0]) cylinder(r = 1.1, h = 0.61, $fn = 20);
    for (y = [5.2, -5.2]) translate([-7.5, y, top]) {  // BOOT / RST
      color("#c0c4ca") translate([-1.5, -2.0, 0]) cube([3.0, 4.0, 1.0]);
      color("#1a1a1a") translate([-0.8, -1.0, 1.0]) cube([1.6, 2.0, 0.5]);
    }
    color("#ff3030") translate([-2.8, 5.4, top]) cube([0.8, 1.6, 0.5]);   // power LED
    color("#3070ff") translate([-2.8, -7.0, top]) cube([0.8, 1.6, 0.5]);  // status LED
  }
}

BAT_XY = BAT_IN_LID ? CASE_BAT_LID : [(BOARD_W - BAT[0]) / 2, BOARD_H - 2.5 - BAT[1]];
BAT_BODY = [BAT[0] - 0.6, BAT[1] - 0.6, BAT_IN_LID ? BAT[2] - 0.6 : 5.0];
// cell position: on the floor, or taped under the lid
BAT_POS = [BAT_XY[0] + 0.3, BAT_XY[1] + 0.3, BAT_IN_LID ? Z_LID_IN - BAT[2] + 0.3 : FLOOR + 0.05];
BAT_LABEL = is_undef(CASE_BAT_LABEL) ? ["LiPo 503040", "3,7 V  600 mAh"] : CASE_BAT_LABEL;
module battery_body(at = false) {
  b = BAT_BODY;
  translate(at ? BAT_POS : [0, 0, 0])
    hull() for (x = [1, b[0] - 1], y = [3, b[1] - 1], z = [1, b[2] - 1]) translate([x, y, z]) sphere(r = 1, $fn = 16);
}
module battery_model() {
  b = BAT_BODY;
  translate(BAT_POS) {
    color("#b9c0c8") battery_body();
    // sealed tab edge with the leads: towards -Y (under the board) or +Y (in the lid)
    color("#b9c0c8") translate([2, BAT_IN_LID ? b[1] - 3 : 0, b[2] / 2 - 0.2]) cube([b[0] - 4, 3, 0.4]);
    color("#2f5fa8") translate([1.5, 5, -0.01]) cube([b[0] - 3, b[1] - 8, 0.05]);
    color("white") translate([b[0] / 2, b[1] / 2 + 2, -0.03]) mirror([1, 0, 0]) linear_extrude(0.03) {
      text(BAT_LABEL[0], size = 2.6, halign = "center", valign = "center", font = "Liberation Sans:style=Bold");
      translate([0, -4]) text(BAT_LABEL[1], size = 1.9, halign = "center", valign = "center", font = "Liberation Sans");
    }
  }
  zp = Z_PCB_TOP + 2.3;
  if (BAT_IN_LID) {
    // leads from the front edge of the cell down in front of it into the plug
    yb = BAT_POS[1] + b[1];
    zb = BAT_POS[2] + b[2] / 2;
    yf = max(yb + 3, J2_FRONT_Y + 7.5);
    for (w = [[J2_XY[0] - 1, BAT_POS[0] + 4, "#d22"], [J2_XY[0] + 1, BAT_POS[0] + 5.4, "#111"]])
      color(w[2]) wire([[w[1], yb - 1, zb], [w[1], yb + 1.5, zb], [w[0], yf, zb - 1], [w[0], yf, zp + 1.5],
                        [w[0], yf - 1, zp], [w[0], J2_FRONT_Y + 5.0, zp]]);
  } else {
    // leads from the cell tab to the JST plug: along the floor, up past the board edge, into the plug
    zb = FLOOR + 2.6;
    for (w = [[J2_XY[0] - 1, BAT_XY[0] + 4, "#d22"], [J2_XY[0] + 1, BAT_XY[0] + 5.4, "#111"]])
      color(w[2]) wire([[w[1], BAT_XY[1] + 1, zb], [w[1], BAT_XY[1] - 2, zb], [w[0], -2.5, zb], [w[0], -5.6, zb + 0.6],
                        [w[0], -6.0, zb + 2.5], [w[0], -6.0, zp - 1], [w[0], -5.6, zp], [w[0], J2_FRONT_Y - 5.0, zp]]);
  }
}

// cutaway: keeps x < CUT_X and paints the cut faces
module cut() { intersection() { children(); translate([OUT[0] - 5, OUT[1] - 5, -5]) cube([CUT_X - OUT[0] + 5, 100, 40]); } }
module cut_face(c) {  // the section of the children in the plane x = CUT_X, as a thin coloured plate
  color(c) translate([CUT_X, 0, 0]) rotate([0, 90, 0]) linear_extrude(0.08, center = true)
    projection(cut = true) rotate([0, -90, 0]) translate([-CUT_X, 0, 0]) children();
}

// Previews can use the finished STLs (make_case.sh writes them first): faster,
// and see-through renders blend cleanly without OpenSCAD's CSG artefacts.
USE_STL = false;
module shell(which) {
  if (USE_STL) import(str(STL_BASE, which, ".stl"), convexity = 10);
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
  ex_lid = max(30, TOP_CLEAR + 18);
  translate([0, 0, BAT_IN_LID ? ex_lid - 14 : 2]) battery_model();
  translate([0, 0, 12]) pcb_model();
  translate([0, 0, ex_lid]) color(SHELL) shell("lid");
} else if (part == "section") {
  cut() { color(SHELL) shell("bottom"); color(SHELL) shell("lid"); pcb_model(); battery_model(); }
  // cut faces from the CSG model: CGAL rejects the sliver triangles that text
  // engravings leave in the exported STLs
  cut_face("#ffb04a") { bottom(); lid(); }
  cut_face("#2e9b5f") pcb_board();
  if (is_undef(SUPERMINI)) {
    cut_face("#e3e6ea") module_can();
    cut_face("#3a3a3a") { module_pcb(); j3_housing(); }
  } else {
    cut_face("#2f5aa8") sm_pcb();
    cut_face("#3a3a3a") { sm_rows(sm(5), Z_PCB_TOP); j3_housing(); }
  }
  cut_face("#cfd6de") battery_body(true);
} else if (part == "xray") {
  pcb_model();
  battery_model();
  color("#7f8794", 0.16) shell("bottom");
  color("#7f8794", 0.16) shell("lid");
} else if (part != "none") {  // assembly: closed device; the internals show through the openings
  color(SHELL) shell("bottom");
  color(SHELL) shell("lid");
  engraving_ink();
  pcb_model();
  battery_model();
}
echo(CASE_SIZE = [OUT[2] - OUT[0], OUT[3] - OUT[1], H], CASE_CENTER = [(OUT[0] + OUT[2]) / 2, (OUT[1] + OUT[3]) / 2, H / 2]);
