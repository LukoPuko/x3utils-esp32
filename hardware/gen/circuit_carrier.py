"""X3-Tuner Mini — carrier board for a plug-in "ESP32-C3 SuperMini".

The ESP32-C3 SuperMini (22.5 x 18 mm, USB-C, ME6211 3.3 V regulator, BOOT on
GPIO9, blue LED on GPIO8) is bought separately and plugged into two 8-pin
sockets. This board adds what the SuperMini lacks: a 1S LiPo with charger,
an on/off switch, the switchable 3.3 V supply for the scooter VCU and the
SWD connector. Every part is placed by the assembler, nothing is hand-soldered.

Build with:  X3_CIRCUIT=circuit_carrier hardware/gen/build.sh   (see cfg.py)

Power concept
  * The SuperMini's 5V pin is wired straight to its USB VBUS (no diode).
  * USB plugged in: VBUS powers the SuperMini and the TP4056 charges the cell.
  * On battery: the cell feeds the 5V pin through Q1 (on/off) and the Schottky
    D1; the SuperMini's ME6211 makes 3.3 V. D1 blocks as soon as USB brings
    5 V, so the cell is never back-fed and charging terminates cleanly.
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
REV = "1.0"

BOARD_W = 38.0
BOARD_H = 50.0              # >= 50 mm so NextPCB's "Rev 0" only needs side rails
CORNER_R = 2.0

POWER_NETS = ["GND", "VBUS", "VBAT", "VBAT_SW", "+3V3", "VTGT"]

LCSC_R = dict(LCSC_R, **{"1M": "C26083"})


def R(ref, value, a, b, sch, pcb, desc=""):
    return Part(ref, "Device:R", value, R0402, LCSC_R[value], {"1": a, "2": b},
                sch, pcb, desc or "Widerstand 0402")


def C(ref, value, a, b, sch, pcb, fp=C0402, desc=""):
    return Part(ref, "Device:C", value, fp, LCSC_C[(value, fp)], {"1": a, "2": b},
                sch, pcb, desc or "Kondensator")


# ── ESP32-C3 SuperMini position ─────────────────────────────────────────────
# Lies with its USB-C pointing to the right board edge. Seen from the top with
# USB-C up, the left header row is 5V, GND, 3V3, GPIO4, 3, 2, 1, 0 and the
# right row GPIO5, 6, 7, 8, 9, 10, 20, 21; the rows are 15.24 mm (600 mil)
# apart and pin 1 of each row is the one next to USB-C. Rotated by 90° the
# "left" row becomes the upper one on this board.
SM_USB_X = 37.5                       # SuperMini PCB edge on the USB-C side
SM_Y = 11.0                           # SuperMini centre line
SM_PIN1_X = SM_USB_X - 3.4            # first pin, 3.4 mm in from the USB end
ROW_5V_Y = SM_Y - 7.62
ROW_IO5_Y = SM_Y + 7.62
SM_LEN, SM_WID = 22.5, 18.0

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

SOCKET_FP = "Connector_PinSocket_2.54mm:PinSocket_1x08_P2.54mm_Vertical"

PARTS = [
    # ── Sockets for the SuperMini ───────────────────────────────────────────
    Part("J1", "Connector_Generic:Conn_01x08", "Sockel SuperMini", SOCKET_FP,
         "C42431840", SOCKET_5V_ROW, (60, 60), (SM_PIN1_X, ROW_5V_Y, 270),
         "Buchsenleiste 1x8 2,54 mm (H 8,5 mm) fuer ESP32-C3 SuperMini"),
    Part("J2", "Connector_Generic:Conn_01x08", "Sockel SuperMini", SOCKET_FP,
         "C42431840", SOCKET_IO5_ROW, (60, 110), (SM_PIN1_X, ROW_IO5_Y, 270),
         "Buchsenleiste 1x8 2,54 mm (H 8,5 mm) fuer ESP32-C3 SuperMini"),

    # ── Charger TP4056 (fed from the SuperMini's 5V pin = USB VBUS) ───────────
    Part("U1", "x3carrier:TP4056", "TP4056", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm",
         "C16581",
         {"1": "GND", "2": "CHG_PROG", "3": "GND", "4": "VBUS", "5": "VBAT",
          "6": "STDBY", "7": "CHRG", "8": "VBUS", "9": "GND"},
         (160, 55), (6.6, 29.0, 0), "Li-Ion Lader 1S, ~360 mA", mfr="TOPPOWER"),
    C("C1", "10uF", "VBUS", "GND", (128, 45), (6.0, 24.6, 0), fp=C0603, desc="Lader Eingang"),
    C("C2", "10uF", "VBAT", "GND", (200, 45), (6.0, 33.3, 0), fp=C0603, desc="Lader Ausgang"),
    R("R1", "3.3k", "CHG_PROG", "GND", (128, 80), (1.4, 28.4, 90), "PROG: I = 1200/R ≈ 364 mA"),
    R("R2", "1k", "VBUS", "LED_R_A", (180, 76), (15.1, 27.0, 0), "LED Laden"),
    Part("D2", "Device:LED", "red", LED0603, "C2286", {"1": "CHRG", "2": "LED_R_A"},
         (188, 92), (12.0, 27.0, 0), "LED rot = lädt"),
    R("R3", "1k", "VBUS", "LED_G_A", (214, 76), (15.1, 28.8, 0), "LED Voll"),
    Part("D3", "Device:LED", "green", "LED_SMD:LED_0805_2012Metric", "C2297",
         {"1": "STDBY", "2": "LED_G_A"}, (188, 106), (12.2, 28.8, 0), "LED grün = voll"),

    # ── Battery, on/off, feed into the 5V pin ────────────────────────────────
    Part("J3", "Connector_Generic:Conn_01x02", "AKKU",
         "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "C295747",
         {"1": "VBAT", "2": "GND"}, (30, 165), (6.0, BOARD_H - 5.0, 0),
         "LiPo 1S mit Schutzschaltung, JST-PH 2.0", mfr="JST"),
    # Switch only drives Q1's gate, so it never carries the load current.
    Part("SW1", "Switch:SW_SPDT", "EIN/AUS", "x3tuner:SW_SPDT_MSK12C02",
         "C431540", {"1": "GND", "2": "PWR_G", "3": None}, (30, 215),
         (2.4, 12.0, 270), "Schiebeschalter Ein/Aus", mfr="SHOU HAN"),
    R("R4", "100k", "VBAT", "PWR_G", (60, 200), (7.4, 4.0, 0), "Q1 aus, wenn Schalter offen"),
    Part("Q1", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "PWR_G", "2": "VBAT", "3": "VBAT_SW"}, (90, 175), (7.6, 7.6, 0),
         "Ein/Aus Akku (P-MOSFET)", mfr="AOS"),
    Part("D1", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598",
         {"1": "VBUS", "2": "VBAT_SW"}, (125, 175), (8.0, 15.2, 0),
         "Akku -> 5V-Pin, sperrt bei USB", mfr="CJ"),
    C("C3", "10uF", "VBAT_SW", "GND", (110, 200), (10.4, 11.0, 90), fp=C0603, desc="Akku-Pfad"),

    # ── Switchable 3.3 V for the VCU + measurements ─────────────────────────
    Part("Q2", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "TGT_EN", "2": "+3V3", "3": "VTGT"}, (200, 165), (33.4, 28.0, 0),
         "VCU-Versorgung schalten (GPIO7 low = an)", mfr="AOS"),
    R("R5", "100k", "+3V3", "TGT_EN", (230, 165), (36.4, 28.0, 90), "VCU aus beim Booten"),
    C("C4", "10uF", "VTGT", "GND", (215, 190), (33.4, 31.4, 0), fp=C0603, desc="VCU-Versorgung"),
    R("R6", "100k", "VTGT", "VTGT_SENSE", (190, 230), (30.0, 32.0, 90), "VCU-Spannung messen"),
    R("R7", "100k", "VTGT_SENSE", "GND", (205, 230), (28.8, 32.0, 90), "VCU-Spannung messen"),
    C("C5", "100nF", "VTGT_SENSE", "GND", (220, 230), (27.6, 32.0, 90), desc="ADC Filter"),
    R("R8", "100k", "VBUS", "VBUS_SENSE", (250, 60), (23.0, 6.8, 0), "USB-Erkennung"),
    R("R9", "100k", "VBUS_SENSE", "GND", (260, 60), (23.0, 8.0, 0), "USB-Erkennung"),
    # 1M/1M on the cell itself: readable while charging with the switch off,
    # ~2 µA standby drain.
    R("R10", "1M", "VBAT", "VBAT_SENSE", (250, 100), (23.0, 11.6, 0), "Akku-Spannung messen"),
    R("R11", "1M", "VBAT_SENSE", "GND", (260, 100), (23.0, 12.8, 0), "Akku-Spannung messen"),
    C("C6", "100nF", "VBAT_SENSE", "GND", (270, 100), (23.0, 14.0, 0), desc="ADC Filter"),

    # ── SWD to the VCU ─────────────────────────────────────────────────────
    R("R12", "100", "NRST", "NRST_T", (350, 60), (23.98, BOARD_H - 9.4, 90), "Serien-R nRST"),
    R("R13", "100", "SWCLK", "SWCLK_T", (362, 60), (26.52, BOARD_H - 9.4, 90), "Serien-R SWCLK"),
    R("R14", "100", "SWDIO", "SWDIO_T", (374, 60), (29.06, BOARD_H - 9.4, 90), "Serien-R SWDIO"),
    Part("J4", "Connector_Generic:Conn_01x05", "SWD-ZIEL",
         "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Horizontal", "C32713264",
         {"1": "VTGT", "2": "SWDIO_T", "3": "SWCLK_T", "4": "NRST_T", "5": "GND"},
         (395, 95), (31.6, BOARD_H - 4.04, 270),
         "Stiftleiste 1x5 gewinkelt zum Scooter (3V3 DIO CLK RST GND)", mfr="hanxia"),
]

# The SuperMini's chip antenna sits at its far end (away from USB-C): no
# copper pour or tracks below it. Rects (x0, y0, x1, y1) in board mm; they stay
# clear of the socket pads.
KEEPOUTS = [
    (11.8, 0.0, 15.3, SM_Y + SM_WID / 2 + 0.5, "ANTENNE_SUPERMINI"),
    (15.3, ROW_5V_Y + 1.25, 19.6, ROW_IO5_Y - 1.25, "ANTENNE_SUPERMINI_2"),
]
VIAS_UNDER = ()

MPN = {
    "C42431840": ("", "PM2.54-1X8PM-H85 (Buchsenleiste 1x8, 2,54 mm, H 8,5 mm)"),
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
    ("X3-Tuner Mini", 6.4, 1.4, 0.9, 0, "F"),
    ("v" + REV, 3.4, 20.8, 0.8, 0, "F"),
    ("ESP32-C3 SuperMini", 26.3, SM_Y - 1.2, 1.0, 0, "F"),
    ("USB-C ->", 30.6, SM_Y + 1.2, 1.0, 0, "F"),
    ("5V", SM_PIN1_X, ROW_5V_Y + 2.1, 0.7, 0, "F"),
    ("IO5", SM_PIN1_X, ROW_IO5_Y - 2.1, 0.7, 0, "F"),
    ("PWR", 5.3, 12.0, 0.8, 90, "F"),
    ("CHG", 12.0, 25.4, 0.7, 0, "F"),
    ("+", 3.7, BOARD_H - 9.0, 1.2, 0, "F"),
    ("-", 8.3, BOARD_H - 9.0, 1.2, 0, "F"),
    ("3V3", 31.6, BOARD_H - 6.5, 0.75, 0, "F"),
    ("DIO", 29.06, BOARD_H - 6.5, 0.75, 0, "F"),
    ("CLK", 26.52, BOARD_H - 6.5, 0.75, 0, "F"),
    ("RST", 23.98, BOARD_H - 6.5, 0.75, 0, "F"),
    ("GND", 21.44, BOARD_H - 6.5, 0.75, 0, "F"),
    ("X3-Tuner Mini v" + REV, 19.0, 26.0, 1.4, 0, "B"),
    ("Traeger fuer ESP32-C3 SuperMini", 19.0, 28.4, 0.9, 0, "B"),
    ("github.com/LukoPuko/x3utils-esp32", 19.0, 30.4, 0.8, 0, "B"),
    ("Akku: 1S LiPo MIT Schutzschaltung, + = Pin 1", 19.0, 34.0, 0.8, 0, "B"),
    ("SuperMini: USB-C zur rechten Kante", 19.0, 36.0, 0.8, 0, "B"),
]

# Spots without parts where a case lid may press the board down.
CASE_POSTS = [(2.5, 21.5), (35.5, 22.0), (36.6, BOARD_H - 2.5), (12.5, BOARD_H - 2.5)]

# KiKit tab positions: left/right edges away from the switch, top edge left of
# the sockets, bottom edge between the battery socket and the SWD header.
PANEL_TABS = [(1.5, 5.5, 180), (1.5, 38.0, 180), (36.5, 24.0, 0), (36.5, 38.0, 0),
              (6.0, 1.5, 90), (15.0, BOARD_H - 1.5, 270)]

# TP4056 exposed pad: GND vias.
THERMAL_VIAS = [(6.6 + dx, 29.0 + dy) for dx in (-0.6, 0.6) for dy in (-0.9, 0.9)]

PWR_FLAG_NETS = ["GND", "VBUS", "VBAT", "+3V3"]

SCH_TEXT = [
    (15, 22, 2.5, "ESP32-C3 SuperMini (aufgesteckt)"),
    (115, 22, 2.5, "Lader TP4056 (aus dem 5V-Pin = USB VBUS)"),
    (15, 140, 2.5, "Akku 1S LiPo (mit Schutz) + Ein/Aus"),
    (175, 140, 2.5, "Schaltbare 3,3 V fuer die VCU + Messung"),
    (235, 22, 2.5, "Messung USB / Akku"),
    (335, 22, 2.5, "SWD zur Scooter-VCU"),
    (335, 140, 2.5, "Hinweise"),
]

NOTES = [
    "Der 5V-Pin des SuperMini ist direkt USB VBUS.",
    "Akkubetrieb: Akku -> Q1 (Schalter) -> D1 -> 5V-Pin.",
    "  D1 sperrt bei USB: Akku wird nur geladen.",
    "Akku MUSS eine eigene Schutzschaltung haben.",
    "Q2 schaltet 3V3 zur VCU (GPIO7 low = an),",
    "  R5 haelt die VCU beim Booten aus.",
    "Ladestrom R1 = 3,3k -> ca. 360 mA.",
    "SWD mit 100 Ohm Serien-R (Kurzschluss/ESD).",
    "GPIO2/8/9 (Strapping) bleiben frei.",
]
