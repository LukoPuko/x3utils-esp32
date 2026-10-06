"""X3-Tuner board — single source of truth for parts, nets and placement.

Everything else (schematic, PCB, BOM, CPL) is generated from this file, so the
schematic and the layout can never drift apart.

Coordinates:
  sch  — schematic position in mm on an A3 sheet (KiCad grid 1.27 mm)
  pcb  — (x, y, rotation°) in mm, origin = board top-left corner, y down
"""

PROJECT = "x3tuner"
TITLE = "X3-Tuner — ESP32-S3 SWD-Programmer mit Akku"
REV = "1.0"

BOARD_W = 38.0
BOARD_H = 60.0
CORNER_R = 2.0

# ── Net classes (track width mm) ─────────────────────────────────────────────
POWER_NETS = ["GND", "VBUS", "VSYS", "VBAT", "BATN", "+3V3", "VTGT", "FET_D"]


class Part:
    def __init__(self, ref, sym, value, fp, lcsc, pins, sch, pcb, desc="",
                 bom=True, mfr=""):
        self.ref = ref
        self.sym = sym          # "Lib:Symbol"
        self.value = value
        self.fp = fp            # "Lib:Footprint"
        self.lcsc = lcsc
        self.pins = pins        # {pin_number: net or None (no-connect)}
        self.sch = sch
        self.pcb = pcb
        self.desc = desc
        self.bom = bom
        self.mfr = mfr


R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
LED0603 = "LED_SMD:LED_0603_1608Metric"

# JLCPCB basic-part LCSC numbers for the jellybean passives.
LCSC_R = {"100": "C25076", "1k": "C11702", "3.3k": "C25890", "5.1k": "C25905",
          "10k": "C25744", "100k": "C25741"}
LCSC_C = {("100nF", C0402): "C1525", ("1uF", C0402): "C52923",
          ("10uF", C0603): "C19702", ("22uF", C0805): "C45783"}


def R(ref, value, a, b, sch, pcb, desc=""):
    return Part(ref, "Device:R", value, R0402, LCSC_R[value], {"1": a, "2": b},
                sch, pcb, desc or "Widerstand 0402")


def C(ref, value, a, b, sch, pcb, fp=C0402, desc=""):
    return Part(ref, "Device:C", value, fp, LCSC_C[(value, fp)], {"1": a, "2": b},
                sch, pcb, desc or "Kondensator")


def LED(ref, color, anode, cathode, sch, pcb, lcsc, desc=""):
    return Part(ref, "Device:LED", color, LED0603, lcsc, {"1": cathode, "2": anode},
                sch, pcb, desc)


# ── ESP32-S3 pin plan (module pad → net) ─────────────────────────────────────
# Chosen for the x3utils job only: the SWD trio sits on the module's bottom
# edge right above the target header (shortest possible SWD traces), the ADC
# inputs are all ADC1 (ADC2 is unusable while WiFi runs), and no strapping,
# flash (26-32) or octal-PSRAM (33-37) pin is used.
ESP_PINS = {
    "1": "GND", "2": "+3V3", "3": "EN",
    "4": None, "5": None, "6": None, "7": None,        # IO4..IO7  free
    "8": None, "9": None, "10": None, "11": None,      # IO15..IO18 free
    "12": "VBUS_SENSE",                                # IO8  USB-present
    "13": "USB_DN", "14": "USB_DP",                    # IO19/IO20 native USB
    "15": None, "16": None,                            # IO3 / IO46 (strapping)
    "17": "VBAT_SENSE",                                # IO9  ADC1_CH8
    "18": None,                                        # IO10 free
    "19": "NRST", "20": "SWCLK", "21": "SWDIO",        # IO11/IO12/IO13
    "22": "TGT_EN",                                    # IO14 target power
    "23": "LED",                                       # IO21 status LED
    "24": None, "25": None, "26": None,                # IO47/IO48/IO45
    "27": "BOOT",                                      # IO0
    "28": None, "29": None, "30": None,                # IO35..37 (PSRAM)
    "31": None, "32": None, "33": None, "34": None, "35": None,
    "36": "RXD0", "37": "TXD0",
    "38": "VTGT_SENSE",                                # IO2  ADC1_CH1
    "39": None,                                        # IO1
    "40": "GND", "41": "GND",
}

# Module centre on the PCB. Antenna points to the top edge.
U1_X, U1_Y = 19.0, 13.5

PARTS = [
    # ── ESP32-S3 core ────────────────────────────────────────────────────────
    Part("U1", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1-N16R8",
         # Library footprint minus its 0.2 mm EPAD vias (JLCPCB 2-layer min
         # drill is 0.3 mm); the PCB script adds 0.3 mm GND vias instead.
         "x3tuner:ESP32-S3-WROOM-1_JLC", "C2913202", ESP_PINS,
         (275, 95), (U1_X, U1_Y, 0),
         "ESP32-S3, 16 MB Flash, 8 MB Octal-PSRAM", mfr="Espressif"),
    C("C1", "22uF", "+3V3", "GND", (235, 35), (6.3, 9.0, 90), fp=C0805,
      desc="3V3 Bulk am Modul"),
    C("C2", "100nF", "+3V3", "GND", (247, 35), (8.4, 9.6, 90)),
    R("R3", "10k", "+3V3", "EN", (235, 150), (3.6, 11.6, 0), "EN Pull-up"),
    C("C3", "1uF", "EN", "GND", (247, 150), (3.6, 12.8, 0), desc="EN Reset-Verzögerung"),
    Part("SW2", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
         "C318884", {"1": "EN", "2": "GND"}, (240, 175), (3.4, 18.6, 90),
         "Taster RESET"),
    Part("SW3", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A",
         "C318884", {"1": "BOOT", "2": "GND"}, (240, 195), (34.6, 18.6, 90),
         "Taster BOOT / Funktion"),
    Part("TP1", "Connector:TestPoint", "TXD0", "TestPoint:TestPoint_Pad_1.0x1.0mm", "",
         {"1": "TXD0"}, (300, 168), (30.6, 9.4, 0), "UART TX (Notfall-Flash)", bom=False),
    Part("TP2", "Connector:TestPoint", "RXD0", "TestPoint:TestPoint_Pad_1.0x1.0mm", "",
         {"1": "RXD0"}, (310, 168), (32.8, 9.4, 0), "UART RX (Notfall-Flash)", bom=False),
    Part("TP3", "Connector:TestPoint", "GND", "TestPoint:TestPoint_Pad_1.0x1.0mm", "",
         {"1": "GND"}, (320, 168), (35.0, 9.4, 0), "GND", bom=False),
    R("R20", "1k", "LED", "LED_A", (300, 190), (24.6, 30.0, 0), "Status-LED"),
    LED("D4", "yellow", "LED_A", "GND", (300, 205), (27.2, 30.0, 180), "C89811",
        "Status-LED gelb"),

    # ── USB-C (Laden + native USB, kein USB-UART-Chip nötig) ──────────────────
    Part("J1", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C",
         "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12", "C165948",
         {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
          "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
          "A5": "CC1", "B5": "CC2",
          "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN",
          "A8": None, "B8": None},
         (45, 70), (3.35, 33.5, 270), "USB-C Buchse 16 Pin", mfr="HRO"),
    R("R1", "5.1k", "CC1", "GND", (85, 45), (10.9, 31.6, 0), "CC1 Pull-down (5V Sink)"),
    R("R2", "5.1k", "CC2", "GND", (95, 45), (10.9, 35.25, 0), "CC2 Pull-down (5V Sink)"),
    # VP goes to +3V3, not VBUS: the S3 keeps its D+ pull-up on while running
    # from the battery, and a VBUS-tied clamp would back-feed VBUS (and half
    # turn off the power-path FET Q1) through it.
    Part("U6", "Power_Protection:SRV05-4", "SRV05-4",
         "Package_TO_SOT_SMD:SOT-23-6", "C85364",
         {"1": "USB_DN", "3": "USB_DP", "2": "GND", "5": "+3V3", "4": None, "6": None},
         (85, 90), (14.0, 34.6, 0), "USB ESD-Schutz", mfr="ProTek"),
    R("R18", "100k", "VBUS", "VBUS_SENSE", (103, 112), (6.4, 23.2, 0), "USB-Erkennung"),
    R("R19", "100k", "VBUS_SENSE", "GND", (113, 112), (6.4, 24.4, 0), "USB-Erkennung"),

    # ── Lader TP4056 + Power-Path ────────────────────────────────────────────
    Part("U2", "x3tuner:TP4056", "TP4056", "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm",
         "C16581",
         {"1": "GND", "2": "CHG_PROG", "3": "GND", "4": "VBUS", "5": "VBAT",
          "6": "STDBY", "7": "CHRG", "8": "VBUS", "9": "GND"},
         (160, 55), (6.6, 45.0, 0), "Li-Ion Lader 1S, ~360 mA", mfr="TOPPOWER"),
    C("C4", "10uF", "VBUS", "GND", (128, 45), (6.0, 40.6, 0), fp=C0603, desc="Lader Eingang"),
    C("C5", "10uF", "VBAT", "GND", (200, 45), (6.0, 48.8, 0), fp=C0603, desc="Lader Ausgang"),
    R("R4", "3.3k", "CHG_PROG", "GND", (128, 80), (1.4, 44.4, 90), "PROG: I = 1200/R ≈ 364 mA"),
    R("R5", "1k", "VBUS", "LED_R_A", (180, 76), (15.1, 43.0, 0), "LED Laden"),
    LED("D2", "red", "LED_R_A", "CHRG", (188, 92), (12.0, 43.0, 0), "C2286", "LED rot = lädt"),
    R("R6", "1k", "VBUS", "LED_G_A", (214, 76), (15.1, 44.8, 0), "LED Voll"),
    Part("D3", "Device:LED", "green", "LED_SMD:LED_0805_2012Metric", "C2297",
         {"1": "STDBY", "2": "LED_G_A"}, (188, 106), (12.2, 44.8, 0), "LED grün = voll"),
    Part("D1", "Device:D_Schottky", "B5819W", "Diode_SMD:D_SOD-123", "C8598",
         {"1": "VSYS", "2": "VBUS"}, (140, 100), (12.0, 39.4, 0),
         "Power-Path USB → System", mfr="CJ"),
    Part("Q1", "Transistor_FET:AO3401A", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "C15127",
         {"1": "VBUS", "2": "VSYS", "3": "VBAT"}, (160, 118), (16.6, 40.8, 0),
         "Power-Path Akku → System (P-MOSFET)", mfr="AOS"),
    R("R7", "100k", "VBUS", "GND", (178, 118), (16.4, 38.2, 0), "Gate Pull-down Q1"),

    # ── Akku + Schutz (BMS) DW01A + FS8205A ─────────────────────────────────
    Part("J2", "Connector_Generic:Conn_01x02", "AKKU",
         "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "C295747",
         {"1": "VBAT", "2": "BATN"}, (30, 165), (6.0, 55.0, 0),
         "LiPo 1S Anschluss JST-PH 2.0", mfr="JST"),
    Part("U3", "x3tuner:DW01A", "DW01A", "Package_TO_SOT_SMD:SOT-23-6", "C351410",
         {"1": "DW_OD", "2": "DW_CS", "3": "DW_OC", "4": None, "5": "DW_VCC", "6": "BATN"},
         (75, 165), (17.0, 55.0, 0), "Akku-Schutz IC", mfr="PUOLOP"),
    # 8205-type dual N-MOSFET, SOT-23-6: 1=S1 2=D 3=S2 4=G2 5=D 6=G1
    # (same pinout as FS8205/FS8205A in SOT-23-6).
    Part("Q2", "x3tuner:8205_SOT-23-6", "HJ8205", "Package_TO_SOT_SMD:SOT-23-6", "C20069150",
         {"1": "BATN", "6": "DW_OD", "3": "GND", "4": "DW_OC", "2": "FET_D", "5": "FET_D"},
         (75, 200), (12.8, 55.0, 0), "Dual N-MOSFET Akku-Schutz", mfr="HJ"),
    R("R8", "100", "VBAT", "DW_VCC", (45, 190), (17.0, 51.6, 0), "DW01A Versorgung"),
    C("C6", "100nF", "DW_VCC", "BATN", (105, 165), (19.6, 52.2, 90), desc="DW01A Versorgung"),
    R("R9", "1k", "DW_CS", "GND", (105, 200), (17.0, 57.8, 0), "DW01A Strommessung"),

    # ── 3,3 V Versorgung ESP + Ein/Aus ─────────────────────────────────────
    Part("SW1", "Switch:SW_SPDT", "EIN/AUS", "Button_Switch_SMD:SW_SPDT_CK_JS102011SAQN",
         "C221660", {"1": "VSYS", "2": "PWR_EN", "3": "GND"}, (30, 250),
         (35.25, 31.0, 90), "Schiebeschalter Ein/Aus", mfr="C&K"),
    Part("U4", "Regulator_Linear:AP2112K-3.3", "ME6211C33M5G-N", "Package_TO_SOT_SMD:SOT-23-5",
         "C82942", {"1": "VSYS", "2": "GND", "3": "PWR_EN", "4": None, "5": "+3V3"},
         (75, 250), (15.4, 30.0, 0), "LDO 3,3 V ESP32 (500 mA)", mfr="Microne"),
    C("C7", "10uF", "VSYS", "GND", (50, 268), (18.2, 30.0, 90), fp=C0603, desc="LDO Eingang"),
    C("C8", "10uF", "+3V3", "GND", (100, 268), (12.6, 30.0, 90), fp=C0603, desc="LDO Ausgang"),

    # ── Ziel-Versorgung (schaltbar) + Messung ───────────────────────────────
    Part("U5", "Regulator_Linear:AP2112K-3.3", "ME6211C33M5G-N", "Package_TO_SOT_SMD:SOT-23-5",
         "C82942", {"1": "VSYS", "2": "GND", "3": "TGT_EN", "4": None, "5": "VTGT"},
         (155, 165), (33.0, 46.6, 0), "LDO 3,3 V Ziel-VCU, per GPIO schaltbar", mfr="Microne"),
    C("C9", "1uF", "VSYS", "GND", (130, 190), (30.4, 46.6, 90), desc="LDO Eingang"),
    C("C10", "10uF", "VTGT", "GND", (180, 190), (33.0, 49.6, 0), fp=C0603, desc="LDO Ausgang"),
    R("R10", "100k", "TGT_EN", "GND", (130, 165), (35.6, 46.6, 90), "Ziel-Strom aus beim Booten"),
    R("R14", "100k", "VTGT", "VTGT_SENSE", (145, 220), (36.6, 39.8, 90), "Ziel-Spannung messen"),
    R("R15", "100k", "VTGT_SENSE", "GND", (160, 220), (35.4, 39.8, 90), "Ziel-Spannung messen"),
    C("C12", "100nF", "VTGT_SENSE", "GND", (175, 220), (34.2, 39.8, 90), desc="ADC Filter"),
    R("R16", "100k", "VBAT", "VBAT_SENSE", (145, 258), (19.4, 34.8, 90), "Akku-Spannung messen"),
    R("R17", "100k", "VBAT_SENSE", "GND", (160, 258), (20.6, 34.8, 90), "Akku-Spannung messen"),
    C("C11", "100nF", "VBAT_SENSE", "GND", (175, 258), (21.8, 34.8, 90), desc="ADC Filter"),

    # ── SWD Ziel-Anschluss ──────────────────────────────────────────────────
    R("R11", "100", "NRST", "NRST_T", (350, 60), (23.98, 50.6, 90), "Serien-R nRST"),
    R("R12", "100", "SWCLK", "SWCLK_T", (362, 60), (26.52, 50.6, 90), "Serien-R SWCLK"),
    R("R13", "100", "SWDIO", "SWDIO_T", (374, 60), (29.06, 50.6, 90), "Serien-R SWDIO"),
    Part("J3", "Connector_Generic:Conn_01x05", "SWD-ZIEL",
         "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Horizontal", "",
         {"1": "VTGT", "2": "SWDIO_T", "3": "SWCLK_T", "4": "NRST_T", "5": "GND"},
         (395, 95), (31.6, 55.96, 270),
         "Stiftleiste 1x5 gewinkelt zum Scooter (3V3 DIO CLK RST GND)"),
]

# Manufacturer part numbers for assemblers that don't use LCSC numbers
# (NextPCB, PCBWay, ...). Passives are generic: any 1 % thick-film resistor /
# X5R-X7R MLCC of that value and size will do.
MPN = {
    "C2913202": ("Espressif", "ESP32-S3-WROOM-1-N16R8"),
    "C16581": ("TOPPOWER", "TP4056-42-ESOP8"),
    "C351410": ("PUOLOP", "DW01A"),
    "C20069150": ("HJ", "HJ8205 (alt. FS8205A SOT-23-6, same pinout)"),
    "C82942": ("Microne", "ME6211C33M5G-N"),
    "C85364": ("ProTek", "SRV05-4-P-T7"),
    "C15127": ("AOS", "AO3401A"),
    "C8598": ("CJ", "B5819W SL"),
    "C165948": ("HRO", "TYPE-C-31-M-12"),
    "C295747": ("JST", "S2B-PH-SM4-TB(LF)(SN)"),
    "C221660": ("C&K", "JS102011SAQN"),
    "C318884": ("XKB", "TS-1187A-B-A-B"),
    "C2286": ("KENTO", "KT-0603R"),
    "C89811": ("NationStar", "NCD0603Y2"),
}

# Silkscreen labels: (text, x, y, size, rotation, layer "F"/"B")
SILK = [
    ("X3-Tuner", 5.2, 3.2, 1.1, 0, "F"),
    ("v" + REV, 33.0, 3.2, 1.0, 0, "F"),
    ("RESET", 7.4, 18.6, 0.8, 90, "F"),
    ("BOOT", 30.6, 18.6, 0.8, 90, "F"),
    ("PWR", 29.7, 31.0, 0.8, 90, "F"),
    ("STAT", 27.2, 31.7, 0.7, 0, "F"),
    ("CHG", 12.0, 41.7, 0.7, 0, "F"),
    ("+", 3.7, 51.0, 1.2, 0, "F"),
    ("-", 8.3, 51.0, 1.2, 0, "F"),
    ("3V3", 31.6, 53.5, 0.75, 0, "F"),
    ("DIO", 29.06, 53.5, 0.75, 0, "F"),
    ("CLK", 26.52, 53.5, 0.75, 0, "F"),
    ("RST", 23.98, 53.5, 0.75, 0, "F"),
    ("GND", 21.44, 53.5, 0.75, 0, "F"),
    ("3V3", 31.6, 53.5, 0.75, 0, "B"),
    ("DIO", 29.06, 53.5, 0.75, 0, "B"),
    ("CLK", 26.52, 53.5, 0.75, 0, "B"),
    ("RST", 23.98, 53.5, 0.75, 0, "B"),
    ("GND", 21.44, 53.5, 0.75, 0, "B"),
    ("SWD -> Scooter-VCU (AT32F415)", 26.5, 51.0, 0.8, 0, "B"),
    ("X3-Tuner v" + REV, 19.0, 9.0, 1.5, 0, "B"),
    ("ESP32-S3 SWD-Programmer", 19.0, 11.4, 1.0, 0, "B"),
    ("github.com/LukoPuko/x3utils-esp32", 19.0, 13.4, 0.8, 0, "B"),
    ("Akku 1S LiPo 3,7 V  (JST-PH, + = Pin 1)", 19.0, 20.0, 0.8, 0, "B"),
    ("Ladeanzeige: rot = laedt, gruen = voll", 19.0, 22.0, 0.8, 0, "B"),
    ("JLCJLCJLCJLC", 19.0, 26.0, 0.8, 0, "B"),
]

# Spots (board coordinates) without components where the case lid presses
# the PCB down; keep them free when moving parts.
CASE_POSTS = [(2.5, 3.0), (35.5, 3.0), (36.3, 57.0), (1.0, 48.5)]

# Extra GND thermal vias (board coordinates): TP4056 exposed pad.
THERMAL_VIAS = [(6.6 + dx, 45.0 + dy) for dx in (-0.6, 0.6) for dy in (-0.9, 0.9)]

# Power flags for ERC (nets driven only by passive pins).
PWR_FLAG_NETS = ["GND", "VBUS", "VSYS", "VBAT", "BATN", "DW_VCC"]

# Free-text blocks on the schematic: (x, y, size, text)
SCH_TEXT = [
    (15, 22, 2.5, "USB-C: Laden + Programmieren (native USB)"),
    (115, 22, 2.5, "Lader TP4056 + Power-Path"),
    (15, 140, 2.5, "Akku 1S LiPo + Schutz (BMS)"),
    (15, 232, 2.5, "Ein/Aus + 3,3 V fuer den ESP32"),
    (115, 140, 2.5, "Schaltbare 3,3 V fuer die VCU + Messung"),
    (222, 22, 2.5, "ESP32-S3-WROOM-1-N16R8"),
    (335, 22, 2.5, "SWD zur Scooter-VCU"),
    (335, 140, 2.5, "Hinweise"),
]

NOTES = [
    "Ladestrom R4 = 3,3k -> ca. 360 mA.",
    "  Akku < 400 mAh: R4 = 4,7k ... 10k.",
    "Q1 + D1 = Power-Path: mit USB laeuft das",
    "  System aus USB, der Akku wird nur geladen.",
    "U5 schaltet die VCU-Versorgung (GPIO14):",
    "  Firmware macht Power-Race automatisch.",
    "VTGT_SENSE erkennt eine extern versorgte VCU,",
    "  dann wird U5 nicht eingeschaltet.",
    "SWD mit 100 Ohm Serien-R (Kurzschluss/ESD).",
    "U6 VP an +3V3 (nicht VBUS): kein Rueckspeisen",
    "  ueber den D+-Pull-up im Akkubetrieb.",
]
