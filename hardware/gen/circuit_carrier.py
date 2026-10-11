"""X3-Tuner Mini — carrier board for a plug-in "ESP32-C3 SuperMini".

The ESP32-C3 SuperMini (22.5 x 18 mm, USB-C, ME6211 3.3 V regulator, BOOT on
GPIO9, blue LED on GPIO8) is bought separately and plugged into two 8-pin
sockets. This board adds what the SuperMini lacks: a 1S LiPo with charger,
an on/off switch, the switchable 3.3 V supply for the scooter VCU and the
SWD connector. Every part is placed by the assembler, nothing is hand-soldered.

The board is a long, narrow "stick" (20.5 x 65 mm): the SuperMini's USB-C at
the front edge, the SWD header at the rear edge, and in between the charger
path under a LiPo that sits in the case lid (see hardware/carrier/case/).

Build with:  X3_CIRCUIT=circuit_carrier hardware/gen/build.sh   (see cfg.py)

Power concept
  * The SuperMini's 5V pin is wired straight to its USB VBUS (no diode).
  * USB plugged in: VBUS powers the SuperMini and the TP4056 charges the cell.
  * On battery: the cell feeds the 5V pin through Q1 (on/off) and the Schottky
    D1; the SuperMini's ME6211 makes 3.3 V. D1 blocks as soon as USB brings
    5 V, so the cell is never back-fed and charging terminates cleanly.
  * Q3 protects against cells with swapped leads (common with cheap JST-PH
    LiPos): it only conducts when + is on pin 1.
  * The cell must have its own protection board (standard for 1S LiPos with a
    JST-PH lead); this board has no DW01A/8205 to keep the part count low.

Coordinates as in circuit.py: sch = schematic mm (A3), pcb = (x, y, rot°),
origin = board top-left, y down.
"""

from circuit import C0402, C0603, LCSC_C, LCSC_R, LED0603, R0402, Part

PROJECT = "x3carrier"
SUBDIR = "carrier"          # hardware/carrier/{kicad,production,docs}
TITLE = "X3-Tuner Mini — Traeger fuer ESP32-C3 SuperMini"
SHORT_NAME = "X3-Tuner Mini"
SCH_COMMENT = "Stecksockel fuer ESP32-C3 SuperMini + Akku/Lader + SWD zur Scooter-VCU"
REV = "1.2"

# ── Board: a long, narrow "stick" ────────────────────────────────────────────
# Front edge (y = 0): the SuperMini's USB-C. Rear edge (y = BOARD_H): the SWD
# header. In between, under the battery: charger path, switch, battery socket.
BOARD_W = 20.5
BOARD_H = 65.0
CORNER_R = 2.0
CX = BOARD_W / 2

POWER_NETS = ["GND", "VBUS", "VBAT", "BAT_IN", "VBAT_SW", "+3V3", "VTGT"]
CHARGER_REF = "U1"          # solid (no thermal relief) exposed pad

LCSC_R = dict(LCSC_R, **{"1M": "C26083"})


def R(ref, value, a, b, sch, pcb, desc=""):
    return Part(ref, "Device:R", value, R0402, LCSC_R[value], {"1": a, "2": b},
                sch, pcb, desc or "Widerstand 0402")


def C(ref, value, a, b, sch, pcb, fp=C0402, desc=""):
    return Part(ref, "Device:C", value, fp, LCSC_C[(value, fp)], {"1": a, "2": b},
                sch, pcb, desc or "Kondensator")


# ── ESP32-C3 SuperMini position ─────────────────────────────────────────────
# Lies along the board with its USB-C at the front edge. Seen from the top
# with USB-C up, the left header row is 5V, GND, 3V3, GPIO4, 3, 2, 1, 0 and
# the right row GPIO5, 6, 7, 8, 9, 10, 20, 21; the rows are 15.24 mm (600 mil)
# apart and pin 1 of each row is the one next to USB-C.
SM_USB_Y = 0.0                        # SuperMini PCB edge on the USB-C side
SM_PIN1_Y = SM_USB_Y + 3.4            # first pin, 3.4 mm in from the USB end
ROW_5V_X = CX - 7.62
ROW_IO5_X = CX + 7.62
SM_LEN, SM_WID = 22.5, 18.0
SM_END_Y = SM_USB_Y + SM_LEN          # far end with the chip antenna

# Socket pin -> net. GPIO2/8/9 are strapping pins (left free), GPIO8 also
# drives the SuperMini's LED, GPIO9 its BOOT button.
SOCKET_5V_ROW = {"1": "VBUS", "2": "GND", "3": "+3V3",
                 "4": "SWCLK",          # GPIO4
                 "5": "VTGT_SENSE",     # GPIO3  ADC1_CH3
                 "6": None,             # GPIO2  strapping
                 "7": "VBUS_SENSE",     # GPIO1  ADC1_CH1
                 "8": "VBAT_SENSE"}     # GPIO0  ADC1_CH0
SOCKET_IO5_ROW = {"1": "SWDIO",         # GPIO5
                  "2": "NRST",          # GPIO6
                  "3": "TGT_EN",        # GPIO7  low = VCU supply on
                  "4": None, "5": None, "6": None, "7": None, "8": None}

# The SuperMini comes WITHOUT soldered pins, so the carrier carries the pins:
# the factory solders two 1x8 male headers, the SuperMini is pushed onto them
# and the case lid clamps it down. Same pad/drill as the socket, so the layout
# is unchanged; only the part (and the 3D height) differ.
SOCKET_FP = "Connector_PinHeader_2.54mm:PinHeader_1x08_P2.54mm_Vertical"
HEADER_LCSC = ""   # 2.54 mm 1x8 male header, THT — add the LCSC no. in the BOM

# ── Rear part (under the battery), from the battery socket to the SWD edge ──
BAT_Y0 = 29.5                         # front end of the battery pocket
JST_Y = 36.4                          # battery socket, opening towards the front
SWD_ROW_Y = BOARD_H - 4.04            # SWD header pin row (pins over the rear edge)
SWD_X = [CX + 5.08 - 2.54 * i for i in range(5)]   # pin 1 (3V3) ... pin 5 (GND)

PARTS = [
    # ── Pin headers the SuperMini is pushed onto ─────────────────────────────
    Part("J1", "Connector_Generic:Conn_01x08", "Stift SuperMini", SOCKET_FP,
         HEADER_LCSC, SOCKET_5V_ROW, (60, 60), (ROW_5V_X, SM_PIN1_Y, 0),
         "Stiftleiste 1x8 2,54 mm fuer ESP32-C3 SuperMini (aufgesteckt)"),
    Part("J2", "Connector_Generic:Conn_01x08", "Stift SuperMini", SOCKET_FP,
         HEADER_LCSC, SOCKET_IO5_ROW, (60, 110), (ROW_IO5_X, SM_PIN1_Y, 0),
         "Stiftleiste 1x8 2,54 mm fuer ESP32-C3 SuperMini (aufgesteckt)"),

    # ── Charger TP4056 (fed from the SuperMini's 5V pin = USB VBUS) ───────────
    # between the socket rows, below the USB end of the SuperMini
    Part("U1", "x3carrier:TP4056", "TP4056", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm",
         "C16581",
         {"1": "GND", "2": "CHG_PROG", "3": "GND", "4": "VBUS", "5": "VBAT",
          "6": "STDBY", "7": "CHRG", "8": "VBUS", "9": "GND"},
         (160, 55), (CX, 6.4, 0), "Li-Ion Lader 1S, ~235 mA", mfr="TOPPOWER"),
    C("C1", "10uF", "VBUS", "GND", (128, 45), (CX - 4.9, 8.0, 90), fp=C0603, desc="Lader Eingang"),
    C("C2", "10uF", "VBAT", "GND", (200, 45), (CX + 4.9, 8.0, 90), fp=C0603, desc="Lader Ausgang"),
    R("R1", "5.1k", "CHG_PROG", "GND", (128, 80), (CX - 4.9, 4.9, 90), "PROG: I = 1200/R ≈ 235 mA"),
    # charge LEDs behind the SuperMini, under a light slit in the lid
    R("R2", "1k", "VBUS", "LED_R_A", (180, 76), (CX + 3.65, 26.2, 0), "LED Laden"),
    Part("D2", "Device:LED", "red", LED0603, "C2286", {"1": "CHRG", "2": "LED_R_A"},
         (188, 92), (CX + 6.35, 26.2, 180), "LED rot = lädt"),
    R("R3", "1k", "VBUS", "LED_G_A", (214, 76), (CX + 3.65, 28.0, 0), "LED Voll"),
    Part("D3", "Device:LED", "green", "LED_SMD:LED_0805_2012Metric", "C2297",
         {"1": "STDBY", "2": "LED_G_A"}, (188, 106), (CX + 6.35, 28.0, 180), "LED grün = voll"),

    # ── Measurements on the ADC pins (front, next to the socket pins) ────────
    R("R8", "100k", "VBUS", "VBUS_SENSE", (250, 60), (CX - 5.25, 12.4, 90), "USB-Erkennung"),
    R("R9", "100k", "VBUS_SENSE", "GND", (260, 60), (CX - 3.95, 12.4, 90), "USB-Erkennung"),
    # 1M/1M on the cell itself: readable while charging with the switch off,
    # ~2 µA standby drain.
    R("R10", "1M", "VBAT", "VBAT_SENSE", (250, 100), (CX - 5.25, 15.6, 90), "Akku-Spannung messen"),
    R("R11", "1M", "VBAT_SENSE", "GND", (260, 100), (CX - 3.95, 15.6, 90), "Akku-Spannung messen"),
    C("C6", "100nF", "VBAT_SENSE", "GND", (270, 100), (CX - 2.65, 15.6, 90), desc="ADC Filter"),

    # ── Battery, reverse protection, on/off, feed into the 5V pin ────────────
    Part("J3", "Connector_Generic:Conn_01x02", "AKKU",
         "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "C295747",
         {"1": "BAT_IN", "2": "GND"}, (30, 165), (CX, JST_Y, 180),
         "LiPo 1S mit Schutzschaltung, JST-PH 2.0, + = Pin 1", mfr="JST"),
    # P-MOSFET as reverse-polarity protection: drain to the socket, gate to GND.
    Part("Q3", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "GND", "2": "VBAT", "3": "BAT_IN"}, (62, 160), (CX + 1.75, 43.6, 0),
         "Verpolschutz Akku (P-MOSFET)", mfr="AOS"),
    # Switch only drives Q1's gate, so it never carries the load current.
    Part("SW1", "Switch:SW_SPDT", "EIN/AUS", "x3tuner:SW_SPDT_MSK12C02",
         "C431540", {"1": "GND", "2": "PWR_G", "3": None}, (30, 215),
         (2.4, 47.0, 270), "Schiebeschalter Ein/Aus", mfr="SHOU HAN"),
    R("R4", "100k", "VBAT", "PWR_G", (60, 200), (6.6, 42.6, 0), "Q1 aus, wenn Schalter offen"),
    Part("Q1", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "PWR_G", "2": "VBAT", "3": "VBAT_SW"}, (90, 175), (7.6, 47.4, 0),
         "Ein/Aus Akku (P-MOSFET)", mfr="AOS"),
    Part("D1", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598",
         {"1": "VBUS", "2": "VBAT_SW"}, (125, 175), (12.6, 47.4, 180),
         "Akku -> 5V-Pin, sperrt bei USB", mfr="CJ"),
    C("C3", "10uF", "VBAT_SW", "GND", (110, 200), (11.6, 51.0, 0), fp=C0603, desc="Akku-Pfad"),

    # ── Switchable 3.3 V for the VCU + measurement ──────────────────────────
    Part("Q2", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "TGT_EN", "2": "+3V3", "3": "VTGT"}, (200, 165), (16.4, 51.0, 0),
         "VCU-Versorgung schalten (GPIO7 low = an)", mfr="AOS"),
    R("R5", "100k", "+3V3", "TGT_EN", (230, 165), (16.9, 47.4, 90), "VCU aus beim Booten"),
    C("C4", "10uF", "VTGT", "GND", (215, 190), (19.1, 51.0, 90), fp=C0603, desc="VCU-Versorgung"),
    R("R6", "100k", "VTGT", "VTGT_SENSE", (190, 230), (14.6, 54.4, 0), "VCU-Spannung messen"),
    R("R7", "100k", "VTGT_SENSE", "GND", (205, 230), (16.6, 54.4, 0), "VCU-Spannung messen"),
    C("C5", "100nF", "VTGT_SENSE", "GND", (220, 230), (18.6, 54.4, 0), desc="ADC Filter"),

    # ── SWD to the VCU ─────────────────────────────────────────────────────
    R("R12", "100", "NRST", "NRST_T", (350, 60), (SWD_X[3], SWD_ROW_Y - 5.36, 90), "Serien-R nRST"),
    R("R13", "100", "SWCLK", "SWCLK_T", (362, 60), (SWD_X[2], SWD_ROW_Y - 5.36, 90), "Serien-R SWCLK"),
    R("R14", "100", "SWDIO", "SWDIO_T", (374, 60), (SWD_X[1], SWD_ROW_Y - 5.36, 90), "Serien-R SWDIO"),
    Part("J4", "Connector_Generic:Conn_01x05", "SWD-ZIEL",
         "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Horizontal", "C32713264",
         {"1": "VTGT", "2": "SWDIO_T", "3": "SWCLK_T", "4": "NRST_T", "5": "GND"},
         (395, 95), (SWD_X[0], SWD_ROW_Y, 270),
         "Stiftleiste 1x5 gewinkelt zum Scooter (3V3 DIO CLK RST GND)", mfr="hanxia"),
]

# The SuperMini's chip antenna sits at its far end, 11 mm above this board:
# no copper pour below it (tracks may pass). Rects (x0, y0, x1, y1) in board mm.
POUR_KEEPOUTS = [(ROW_5V_X + 1.4, SM_END_Y - 4.5, ROW_IO5_X - 1.4, SM_END_Y + 0.6, "ANTENNE_SUPERMINI")]
KEEPOUTS = []
VIAS_UNDER = ()

MPN = {
    "": ("", "Stiftleiste 1x8 2,54 mm THT (LCSC-Nr. ergaenzen)"),
    "C16581": ("TOPPOWER", "TP4056-42-ESOP8"),
    "C15127": ("AOS", "AO3401A"),
    "C8598": ("CJ", "B5819W SL"),
    "C295747": ("JST", "S2B-PH-SM4-TB(LF)(SN)"),
    "C431540": ("SHOU HAN", "MSK12C02"),
    "C2286": ("KENTO", "KT-0603R"),
    "C2297": ("KENTO", "KT-0805G"),
    "C32713264": ("hanxia", "HX PZ2.54-1x5P WZ (1x5 2.54 mm, gewinkelt, THT)"),
}

# Silkscreen: (text, x, y, size, rotation, layer)
SILK = [
    ("USB-C", CX, 1.4, 0.8, 0, "F"),
    ("5V", ROW_5V_X, SM_PIN1_Y - 2.2, 0.7, 0, "F"),
    ("IO5", ROW_IO5_X, SM_PIN1_Y - 2.2, 0.7, 0, "F"),
    ("SuperMini", CX, 19.6, 0.9, 0, "F"),
    ("CHG", CX + 6.35, 24.4, 0.7, 0, "F"),
    ("+", CX + 4.9, JST_Y + 1.8, 1.2, 0, "F"),
    ("-", CX - 4.9, JST_Y + 1.8, 1.2, 0, "F"),
    ("PWR", 5.3, 51.6, 0.7, 0, "F"),
    ("v" + REV, 2.6, 33.0, 0.7, 90, "F"),
    ("3V3", SWD_X[0], SWD_ROW_Y - 2.5, 0.75, 0, "F"),
    ("DIO", SWD_X[1], SWD_ROW_Y - 2.5, 0.75, 0, "F"),
    ("CLK", SWD_X[2], SWD_ROW_Y - 2.5, 0.75, 0, "F"),
    ("RST", SWD_X[3], SWD_ROW_Y - 2.5, 0.75, 0, "F"),
    ("GND", SWD_X[4], SWD_ROW_Y - 2.5, 0.75, 0, "F"),
    ("X3-Tuner Mini v" + REV, 4.4, 38.0, 1.4, 90, "B"),
    ("Traeger fuer ESP32-C3 SuperMini", 7.0, 38.0, 0.9, 90, "B"),
    ("github.com/LukoPuko/x3utils-esp32", 9.2, 38.0, 0.8, 90, "B"),
    ("Akku: 1S LiPo MIT Schutz, + = Pin 1", 12.2, 38.0, 0.8, 90, "B"),
    ("SuperMini: USB-C zur Stirnseite", 14.4, 38.0, 0.8, 90, "B"),
]

# Spots without parts where a case lid may press the board down.
CASE_POSTS = [(2.4, 26.0)]

# KiKit tab positions: long sides away from the switch, the front edge between
# the socket rows (the rear edge carries the SWD pins).
PANEL_TABS = [(1.5, 12.0, 180), (1.5, 31.0, 180), (1.5, 58.0, 180),
              (BOARD_W - 1.5, 12.0, 0), (BOARD_W - 1.5, 33.0, 0), (BOARD_W - 1.5, 58.0, 0),
              (CX, 1.5, 90)]
# NextPCB "Rev 0" wants >= 50 x 50 mm: side rails wide enough for that
NEXTPCB_RAIL = 12.0

# TP4056 exposed pad: GND vias.
THERMAL_VIAS = [(CX + dx, 6.4 + dy) for dx in (-0.6, 0.6) for dy in (-0.9, 0.9)]

PWR_FLAG_NETS = ["GND", "VBUS", "VBAT", "+3V3"]

SCH_TEXT = [
    (15, 22, 2.5, "ESP32-C3 SuperMini (aufgesteckt)"),
    (115, 22, 2.5, "Lader TP4056 (aus dem 5V-Pin = USB VBUS)"),
    (15, 140, 2.5, "Akku 1S LiPo (mit Schutz) + Verpolschutz + Ein/Aus"),
    (175, 140, 2.5, "Schaltbare 3,3 V fuer die VCU + Messung"),
    (235, 22, 2.5, "Messung USB / Akku"),
    (335, 22, 2.5, "SWD zur Scooter-VCU"),
    (335, 140, 2.5, "Hinweise"),
]

NOTES = [
    "Der 5V-Pin des SuperMini ist direkt USB VBUS.",
    "Akkubetrieb: Akku -> Q3 -> Q1 (Schalter) -> D1 -> 5V-Pin.",
    "  D1 sperrt bei USB: Akku wird nur geladen.",
    "Q3 = Verpolschutz: leitet nur mit + an Pin 1.",
    "Akku MUSS eine eigene Schutzschaltung haben.",
    "Q2 schaltet 3V3 zur VCU (GPIO7 low = an),",
    "  R5 haelt die VCU beim Booten aus.",
    "Ladestrom R1 = 5,1k -> ca. 235 mA.",
    "SWD mit 100 Ohm Serien-R (Kurzschluss/ESD).",
    "GPIO2/8/9 (Strapping) bleiben frei.",
]

# ── 3D case (make_case_data.py -> hardware/carrier/case/board_data.scad) ─────
# The SuperMini has no pins of its own; it is pushed onto the carrier's 2.54 mm
# male headers and rests on their 2.5 mm plastic, so its PCB underside is 2.5 mm
# above this board (much flatter than a socketed module). The header pins poke
# ~5 mm above the module; the lid clears them. A LiPo up to 21 x 33 x 7 mm
# (e.g. 602030/702030, ~400 mAh) is taped into a pocket under the lid, above
# the rear of the board.
SM_HEIGHT = 2.5            # SuperMini PCB underside above the carrier top (header plastic)
SM_PCB_T = 1.0
SM_USB_OVERHANG = 2.0       # USB-C shell beyond the SuperMini's PCB edge
SM_TOP = SM_HEIGHT + SM_PCB_T   # SuperMini top surface above the carrier
# TOP_CLEAR is driven by the LiPo over the rear: its underside must clear the
# JST socket (the tallest rear part, ~4.9 mm). Pocket 8 mm holds a 6-7 mm cell;
# a thicker 8 mm cell (802030) needs CASE_TOP_CLEAR ~ 15.
TOP_CLEAR = 13.5            # carrier top to lid underside
BAT_POCKET = (BOARD_W + 0.7, BOARD_H - 2.2 - BAT_Y0, 8.0)   # width, length, thickness
CASE = dict(
    name="x3mini",
    title="X3-Tuner Mini Gehäuse",
    # which reference is which connector on this board (X3-Tuner: J1/J2/J3)
    refs=dict(usb=None, bat="J3", swd="J4", switch="SW1", reset=None, boot=None,
              led_stat=None, led_chg=("D2", "D3")),
    own_model=("J1", "J2", "J3", "J4", "SW1"),   # drawn by the case model itself
    supermini=dict(x=CX, usb_y=SM_USB_Y, len=SM_LEN, wid=SM_WID, height=SM_HEIGHT,
                   pcb_t=SM_PCB_T, pin1=SM_PIN1_Y - SM_USB_Y, row=7.62,
                   usb_overhang=SM_USB_OVERHANG),
    # battery pocket under the lid: front end at BAT_Y0, reaching to the rear
    battery=dict(y0=BAT_Y0, size=BAT_POCKET, label=["LiPo 602030", "3,7 V  400 mAh"]),
    led_slits=("chg",),     # only the carrier's charge LED shows through the lid
    pin_buttons=(),         # no RESET/BOOT access: the module is fully enclosed
    windows=[],             # no openings over the SuperMini (no readout/flash access)
    # blocks hanging from the lid: (x0, y0, x1, y1, bottom above the board top)
    lid_blocks=[
        # clamp the SuperMini down onto the headers: two ribs at the rear corners,
        # behind the last pins and clear of the centre chip antenna
        (CX - 8.5, SM_END_Y - 1.1, CX - 3.0, SM_END_Y - 0.2, SM_TOP),
        (CX + 3.0, SM_END_Y - 1.1, CX + 8.5, SM_END_Y - 0.2, SM_TOP),
        # hold the rear of the board down on the SWD header body
        (SWD_X[4] - 0.8, BOARD_H - 2.0, SWD_X[0] + 0.8, BOARD_H - 0.8, 2.65),
        # front battery stop, from the lid down to the battery underside
        (1.0, BAT_Y0 - 0.8, BOARD_W - 1.0, BAT_Y0, TOP_CLEAR - BAT_POCKET[2]),
    ],
    # renders: (file, part, eye offset, look-at offset from the case centre)
    cameras=[("case-assembly.png", "assembly", (-62, 70, 52), (0, 0, 0)),
             ("case-xray.png", "xray", (-62, 70, 52), (0, 0, 0)),
             ("case-xray-bottom.png", "xray", (-70, -72, -55), (0, 0, 0)),
             ("case-section.png", "section", (80, 30, 26), (0, 0, 0)),
             ("case-exploded.png", "exploded", (-66, 74, 58), (0, 0, 12))],
    sheet=("Schalter", "Rechts", "Stirnseite USB-C"),
    scad=dict(
        CASE_BAT_GAP=3.2,           # THT pin-header / SWD tails below the board
        CASE_TOP_CLEAR=TOP_CLEAR,   # driven by the 8 mm LiPo under the lid
        CASE_FACET_IN=1.0,          # room for the battery edges under the lid
        CASE_CORNER=4.0,            # corner facets clear the board / SuperMini corners
        CASE_USB_HOLE=[4.8, 10.2],  # tolerance for the SuperMini height
        CASE_USB_LEADIN=[6.8, 12.4, 1.2],  # room for the cable's overmould
        CASE_SNAP_Y=[5, 32, 56],    # clear of the switch slot
        CASE_POST_D=3.0,            # long post, so a bit thicker
        CASE_LOGO_SUB="MINI · x3utils-esp32",
        CASE_LOGO_ROT=90,
        CASE_LABELS_UP=True,
        CASE_PORT_BLOCKS=[[0.5, SWD_X[4] - 1.0], [SWD_X[0] + 1.0, BOARD_W - 0.5]],  # overlap the side strips
        CASE_CUT_X=round((SWD_X[1] + SWD_X[2]) / 2, 2),
    ),
)
