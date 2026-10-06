// X3-Tuner case — two-part snap-fit enclosure for the PCB plus a 1S LiPo.
//
//   part = "bottom"   tray: battery bay, PCB supports, lower half of the ports
//   part = "lid"      lid: flexure buttons, light pipes, engraving, snap lip
//   part = "print"    both parts laid out for printing (lid upside down)
//   part = "assembly" / "exploded"   preview with a simplified PCB + battery
//
// All board-related positions come from board_data.scad, which
// hardware/gen/make_case_data.py generates from hardware/gen/circuit.py.
// Print: PLA or PETG, 0.2 mm layers, no supports, lid top face on the bed.

include <board_data.scad>

part = "assembly";

/* [Battery] */
// Pocket for a 503040 LiPo (30 x 40 x 5 mm nominal, ~600 mAh) incl. margin.
// Anything up to [34, 43] mm footprint fits under the 54.5 mm board.
BAT = [31.5, 42.0, 5.6];

/* [Shell] */
WALL = 1.6;       // side walls
FLOOR = 1.2;      // bottom thickness
LID = 1.4;        // top thickness
GAP = 0.35;       // PCB edge to inner wall
BAT_GAP = 1.5;    // battery top to PCB underside (THT tails, USB-C shell legs)
TOP_CLEAR = 5.4;  // PCB top to lid underside (tallest part: JST-PH, ~4.9 mm)
END_EXT = 7.0;    // room behind the board edge: SWD pins + battery plug
R_OUT = 4.0;      // corner radius (plan view)
CHAMFER = 0.8;    // top/bottom edge chamfer
LIP_T = 0.8;      // snap lip thickness
LIP_H = 2.2;      // snap lip height
FIT = 0.15;       // print clearance lip <-> skirt
SKIN = 0.6;       // material left over the LEDs (light shines through)
BTN_H = 1.5;      // tactile switch height (TS-1187A)

$fn = 48;

Z_PCB_BOT = FLOOR + BAT[2] + BAT_GAP;
Z_PCB_TOP = Z_PCB_BOT + PCB_T;
H = Z_PCB_TOP + TOP_CLEAR + LID;
Z_SPLIT = Z_PCB_TOP;

IN = [-GAP, -END_EXT, BOARD_W + GAP, BOARD_H + GAP];       // x0 y0 x1 y1
OUT = [IN[0] - WALL, IN[1] - WALL, IN[2] + WALL, IN[3] + WALL];
R_IN = R_OUT - WALL;

// ── helpers ─────────────────────────────────────────────────────────────────
module rrect2d(b, r) {
  hull() for (x = [b[0] + r, b[2] - r], y = [b[1] + r, b[3] - r]) translate([x, y]) circle(r);
}
module slab(b, r, z0, z1) { translate([0, 0, z0]) linear_extrude(z1 - z0) rrect2d(b, r); }
function inset(b, d) = [b[0] + d, b[1] + d, b[2] - d, b[3] - d];

// Rounded box with chamfered top and bottom edges.
module body(b, r, z0, z1, ch) {
  hull() {
    slab(inset(b, ch), r - ch, z0, z0 + 0.01);
    slab(b, r, z0 + ch, z1 - ch);
    slab(inset(b, ch), r - ch, z1 - 0.01, z1);
  }
}
module rbox(c, s, r) {  // centred rounded box
  translate(c) hull() for (x = [-s[0] / 2 + r, s[0] / 2 - r], y = [-s[1] / 2 + r, s[1] / 2 - r])
    translate([x, y, -s[2] / 2]) cylinder(r = r, h = s[2]);
}

// ── port cut-outs (through both halves) ─────────────────────────────────────
module ports() {
  // USB-C on whichever side the board puts it
  usb_in = USB_RIGHT ? IN[2] : IN[0];
  usb_out = USB_RIGHT ? OUT[2] : OUT[0];
  translate([usb_out, USB_Y, Z_PCB_TOP + 1.63]) rotate([0, USB_RIGHT ? -90 : 90, 0]) {
    rbox([0, 0, (WALL + 1.2) / 2 - 1], [3.9, 9.7, WALL + 1.2 + 1], 1.5);
    rbox([0, 0, 0.1], [5.4, 11.2, 1.4], 2.2);  // soft recess on the outside
  }
  // slide switch lever + finger scoop
  sw_in = SW1_RIGHT ? IN[2] : IN[0];
  sw_out = SW1_RIGHT ? OUT[2] : OUT[0];
  dir = SW1_RIGHT ? 1 : -1;
  translate([min(sw_in, sw_out) - (SW1_RIGHT ? 0.5 : 1), SW1_Y - 3.6, Z_PCB_TOP - 0.4])
    cube([WALL + 1.5, 7.2, 3.0]);
  translate([sw_out + dir * 2.4, SW1_Y, Z_PCB_TOP + 1.1]) scale([1, 1.6, 1]) sphere(r = 3.4);
  // SWD port, end wall: a 5-pin Dupont housing slides over the header pins
  pins_c = J3_PIN1_X - 2 * J3_PITCH;
  translate([pins_c, OUT[1] - 1, Z_PCB_TOP + 1.27]) rotate([-90, 0, 0]) {
    rbox([0, 0, (IN[1] - OUT[1] + 1.2) / 2], [13.7, 3.4, IN[1] - OUT[1] + 1.2], 0.6);
    rbox([0, 0, 0.8], [15.2, 4.8, 1.6], 1.2);
  }
}

// ── bottom tray ─────────────────────────────────────────────────────────────
module lip_ring(extra = 0) {
  difference() {
    rrect2d(inset(IN, -LIP_T - extra), R_IN + LIP_T + extra);
    rrect2d(IN, R_IN);
  }
}
SNAPS = [[IN[0], 12], [IN[0], 46], [IN[2], 12], [IN[2], 46]];

// Wedge-shaped snap bump on the outer face of the lip (grow > 0: the matching
// groove in the lid). Base sits 0.1 mm inside the lip for a clean union.
module snap(s, grow = 0) {
  dir = s[0] < 1 ? -1 : 1;
  x0 = s[0] + dir * (LIP_T - 0.1);
  z = Z_SPLIT + LIP_H / 2;
  hull() {
    translate([min(x0, x0 + dir * 0.01), s[1] - 2.5 - grow, z - 0.6 - grow]) cube([0.01, 5 + 2 * grow, 1.2 + 2 * grow]);
    translate([x0 + dir * (0.55 + grow) - 0.005, s[1] - 2.5 - grow, z - 0.05 - grow / 2]) cube([0.01, 5 + 2 * grow, 0.1 + grow]);
  }
}

module bottom() {
  difference() {
    union() {
      intersection() {
        body(OUT, R_OUT, 0, H, CHAMFER);
        translate([OUT[0] - 1, OUT[1] - 1, -1]) cube([OUT[2] - OUT[0] + 2, OUT[3] - OUT[1] + 2, Z_SPLIT + 1]);
      }
      // snap lip rising above the split, inner half of the wall
      translate([0, 0, Z_SPLIT - 0.01]) linear_extrude(LIP_H) lip_ring();
      for (s = SNAPS) snap(s);
    }
    slab(IN, R_IN, FLOOR, H);  // cavity
    ports();
  }
  // PCB supports: side strips, antenna-end strip, two blocks at the port end
  // (gaps leave room for the battery wire and the SWD header tails)
  // (strips reach 0.3 mm into the walls so the union stays manifold)
  for (b = [[IN[0] - 0.3, 0.5, 1.0, BOARD_H - 0.5], [BOARD_W - 1.0, 0.5, IN[2] + 0.3, BOARD_H - 0.5],
            [0.5, BOARD_H - 1.2, BOARD_W - 0.5, IN[3] + 0.3], [12, 0, 18, 1.2], [34, 0, 37.5, 1.2]])
    translate([b[0], b[1], FLOOR - 0.01]) cube([b[2] - b[0], b[3] - b[1], Z_PCB_BOT - FLOOR + 0.01]);
  // battery bay: low fences so the cell cannot slide
  bx0 = (BOARD_W - BAT[0]) / 2;
  by0 = BOARD_H - 2.5 - BAT[1];
  for (f = [[bx0 - 1.2, by0, 1.2, BAT[1]], [bx0 + BAT[0], by0, 1.2, BAT[1]],
            [bx0 + 6, by0 - 1.2, 6, 1.2], [bx0 + BAT[0] - 12, by0 - 1.2, 6, 1.2]])
    translate([f[0], f[1], FLOOR - 0.01]) cube([f[2], f[3], 2.0]);
}

// ── lid ─────────────────────────────────────────────────────────────────────
Z_LID_IN = H - LID;
BTN_T = [5.6, 8.0];  // flexure tongue size

module tongue_slot(c) {  // U-shaped cut, hinge on the +Y side
  translate([c[0], c[1], Z_LID_IN - 1]) difference() {
    translate([-BTN_T[0] / 2 - 0.55, -BTN_T[1] / 2 - 0.55, 0]) cube([BTN_T[0] + 1.1, BTN_T[1] + 0.55, LID + 2]);
    translate([-BTN_T[0] / 2, -BTN_T[1] / 2, -1]) cube([BTN_T[0], BTN_T[1] + 2, LID + 4]);
  }
}
module button_plunger(c) {
  translate([c[0], c[1], Z_PCB_TOP + BTN_H + 0.25]) cylinder(d = 2.6, h = Z_LID_IN - (Z_PCB_TOP + BTN_H + 0.25) + 0.01);
}
module light_tube(c, s) {  // walls around a LED so colours don't bleed
  translate([c[0] - s[0] / 2 - 0.8, c[1] - s[1] / 2 - 0.8, Z_PCB_TOP + 1.0])
    difference() {
      cube([s[0] + 1.6, s[1] + 1.6, Z_LID_IN - Z_PCB_TOP - 1.0 + 0.01]);
      translate([0.8, 0.8, -1]) cube([s[0], s[1], 20]);
    }
}
module led_window(c, s) {
  translate([c[0] - s[0] / 2, c[1] - s[1] / 2, Z_PCB_TOP]) cube([s[0], s[1], H - SKIN - Z_PCB_TOP]);
}
module engrave() {
  d = 0.5;
  translate([BOARD_W / 2, BOARD_H - 3.4, H - d]) linear_extrude(d + 1)
    text("X3·TUNER", size = 3.6, font = "Liberation Sans:style=Bold", halign = "center", valign = "center", spacing = 1.1);
  for (i = [0:4]) translate([J3_PIN1_X - i * J3_PITCH, IN[1] + 3.2, H - d]) linear_extrude(d + 1)
    rotate(90) text(J3_LABELS[i], size = 1.9, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
  for (c = [SW2_XY, SW3_XY]) translate([c[0], c[1], H - 0.4]) linear_extrude(1)
    difference() { circle(d = 3.4); circle(d = 2.4); }
  translate([SW2_XY[0], SW2_XY[1] - 6.4, H - d]) linear_extrude(d + 1)
    text("RST", size = 1.9, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
  translate([SW3_XY[0], SW3_XY[1] - 6.4, H - d]) linear_extrude(d + 1)
    text("BOOT", size = 1.9, font = "Liberation Sans:style=Bold", halign = "center", valign = "center");
}

module lid() {
  difference() {
    union() {
      difference() {
        intersection() {
          body(OUT, R_OUT, 0, H, CHAMFER);
          translate([OUT[0] - 1, OUT[1] - 1, Z_SPLIT]) cube([OUT[2] - OUT[0] + 2, OUT[3] - OUT[1] + 2, H]);
        }
        slab(IN, R_IN, -1, Z_LID_IN);
        // room for the tray's snap lip (+ clearance)
        translate([0, 0, Z_SPLIT - 0.01]) linear_extrude(LIP_H + FIT) lip_ring(FIT);
        for (s = SNAPS) snap(s, 0.15);
      }
      for (p = LID_POSTS) translate([p[0], p[1], Z_PCB_TOP + 0.1]) cylinder(d = 2.0, h = Z_LID_IN - Z_PCB_TOP);
      light_tube(LED_STAT_XY, [2.6, 2.0]);
      light_tube(LED_CHG_XY, [3.4, 4.2]);
      for (c = [SW2_XY, SW3_XY]) button_plunger(c);
    }
    for (c = [SW2_XY, SW3_XY]) tongue_slot(c);
    led_window(LED_STAT_XY, [2.6, 2.0]);
    led_window(LED_CHG_XY, [3.4, 4.2]);
    ports();
    engrave();
  }
}

// ── simplified board + battery for previews ─────────────────────────────────
module pcb_model() {
  color("#1f6f43") slab([0, 0, BOARD_W, BOARD_H], BOARD_R, Z_PCB_BOT, Z_PCB_TOP);
  t = Z_PCB_TOP;
  color("silver") translate([U1_XY[0] - 9, MODULE_BOTTOM_Y, t]) cube([18, ANTENNA_Y - MODULE_BOTTOM_Y, 3.2]);
  color("#222") translate([U1_XY[0] - 9, ANTENNA_Y, t]) cube([18, 6.0, 0.8]);
  color("silver") translate([USB_RIGHT ? USB_FRONT_X - 7.3 : USB_FRONT_X, USB_Y - 4.47, t]) cube([7.3, 8.94, 3.26]);
  color("white") translate([J2_XY[0] - 3.95, J2_FRONT_Y, t]) cube([7.9, 7.6, 4.9]);
  color("#ddd") translate([J2_XY[0] - 3.0, J2_FRONT_Y - 5.0, t + 0.6]) cube([6.0, 5.0, 3.4]);  // plug
  color("#111") translate([J3_PIN1_X - 4 * J3_PITCH - 1.27, J3_ROW_Y - 4.04, t]) cube([12.7, 2.54, 2.5]);
  for (i = [0:4]) color("gold") translate([J3_PIN1_X - i * J3_PITCH - 0.32, J3_TIP_Y, t + 0.95]) cube([0.64, J3_ROW_Y - J3_TIP_Y, 0.64]);
  sw_body_x = SW1_RIGHT ? BOARD_W - 3.2 : 0.35;
  color("#333") translate([sw_body_x, SW1_Y - 3.35, t]) cube([2.85, 6.7, 1.4]);
  color("#333") translate([SW1_RIGHT ? BOARD_W - 0.1 : SW1_LEVER_X, SW1_Y - 0.75, t + 0.2])
    cube([abs(SW1_LEVER_X - (SW1_RIGHT ? BOARD_W - 0.1 : 0.45)), 1.5, 1.0]);
  for (c = [SW2_XY, SW3_XY]) color("#444") translate([c[0] - 2.55, c[1] - 2.55, t]) cube([5.1, 5.1, BTN_H]);
  color("red") translate([LED_CHG_XY[0] - 0.8, LED_CHG_XY[1] + 0.2, t]) cube([1.6, 0.8, 0.6]);
  color("lime") translate([LED_CHG_XY[0] - 1.0, LED_CHG_XY[1] - 1.3, t]) cube([2.0, 1.25, 0.6]);
  color("yellow") translate([LED_STAT_XY[0] - 0.8, LED_STAT_XY[1] - 0.4, t]) cube([1.6, 0.8, 0.6]);
}
module battery_model() {
  color("#9aa4b5") translate([(BOARD_W - BAT[0]) / 2 + 0.3, BOARD_H - 2.5 - BAT[1] + 0.3, FLOOR]) cube([BAT[0] - 0.6, BAT[1] - 0.6, 5.0]);
}

if (part == "bottom") bottom();
else if (part == "lid") lid();
else if (part == "print") {
  bottom();
  translate([OUT[2] - OUT[0] + 6, 0, H]) mirror([0, 0, 1]) translate([0, 0, 0]) lid();
} else if (part == "exploded") {
  color("#2b2f36") bottom();
  battery_model();
  translate([0, 0, 6]) pcb_model();
  translate([0, 0, 20]) color("#e9ecef") lid();
} else {
  color("#2b2f36") bottom();
  battery_model();
  pcb_model();
  color("#e9ecef", 0.35) lid();
}
