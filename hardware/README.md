# X3-Tuner – eigene Platine für x3utils-esp32

Ein **All-in-one-Gerät** für die AT32F415-VCU der X3-Scooter-Familie (ZT3 Pro,
Max G3, F3 / F3 Pro): ESP32-S3 mit viel RAM, eigener Akku mit Lade- und
Schutzschaltung, schaltbare 3,3-V-Versorgung für die VCU und ein SWD-Stecker.
Ersetzt **ST-LINK, PC und Kabelsalat** – bedient wird alles per Handy-Browser
über WLAN (Firmware: dieses Repository, Environment `x3tuner`).

| Oberseite | Unterseite |
|---|---|
| ![Oberseite](docs/pcb-top.png) | ![Unterseite](docs/pcb-bottom.png) |

[Schaltplan (PDF)](docs/x3tuner-schematic.pdf) ·
[Bestückungsplan (PDF)](docs/x3tuner-assembly.pdf) ·
[Fertigungsdaten](production/)

> [!IMPORTANT]
> **Status: Design fertig, noch nicht gefertigt.** Die Platine besteht den
> KiCad-DRC (0 Fehler, 0 offene Verbindungen) und der Schaltplan wird
> automatisch gegen die Netzliste geprüft – ein gebauter Prototyp existiert
> aber noch nicht. Bitte zuerst **2–5 Stück** bestellen und testen. Was du vor
> der Bestellung prüfen solltest, steht unter [Vor der Bestellung prüfen](#vor-der-bestellung-prüfen).

---

## Was drauf ist

| Block | Lösung | Warum |
|---|---|---|
| MCU | **ESP32-S3-WROOM-1-N16R8**: 16 MB Flash, **8 MB PSRAM** | viel RAM, WLAN, natives USB |
| USB | USB-C direkt an GPIO19/20 (natives USB des S3) | kein CH340/CP2102 nötig → günstiger |
| Laden | **TP4056**, ca. 360 mA (R4 = 3,3 kΩ), LEDs rot = lädt, grün = voll | Standard, sehr billig |
| Akku-Schutz (BMS) | **DW01A + 8205-Dual-MOSFET** | Schutz vor Über- und Tiefentladung, Überstrom und Kurzschluss |
| Power-Path | P-MOSFET AO3401A + Schottky B5819W | mit USB läuft das Gerät aus USB, der Akku wird nur geladen |
| 3,3 V ESP | ME6211 (500 mA LDO), Ein/Aus-Schiebeschalter am Enable-Pin | kleiner Ruhestrom, Laden auch im ausgeschalteten Zustand |
| 3,3 V VCU | **zweiter ME6211, per GPIO14 schaltbar**, mit Spannungsmessung | Firmware schaltet die VCU selbst ein → **automatischer Power-Race** |
| SWD | 1×5-Stiftleiste 2,54 mm (3V3 · DIO · CLK · RST · GND), 100 Ω Serienwiderstände | Dupont-Kabel wie beim ST-LINK |
| Bedienung | RESET, BOOT, Status-LED (gelb) | |
| Messung | Akkuspannung, USB vorhanden, Spannung an der VCU (alle ADC1) | Akkuanzeige in der Web-Oberfläche, Schutz gegen Doppelversorgung |

**Platine:** 38 × 60 mm, 2 Lagen, 1,6 mm, alle SMD-Teile auf der Oberseite
(einseitige Bestückung = günstig). Unten durchgehende Massefläche – dort klebt
der Akku. Antenne am oberen Rand, ohne Kupfer darunter.

### Pinbelegung ESP32-S3

| GPIO | Funktion | | GPIO | Funktion |
|---|---|---|---|---|
| IO11 | nRST (zur VCU, über 100 Ω) | | IO2 | VTGT_SENSE (Spannung an der VCU, ½) |
| IO12 | SWCLK (über 100 Ω) | | IO8 | VBUS_SENSE (USB steckt, ½) |
| IO13 | SWDIO (über 100 Ω) | | IO9 | VBAT_SENSE (Akkuspannung, ½) |
| IO14 | TGT_EN (VCU-Versorgung ein) | | IO21 | Status-LED |
| IO0 | BOOT-Taste | | IO19/20 | USB D−/D+ |
| EN | RESET-Taste | | IO43/44 | UART0 (Testpads TP1/TP2) |

Die SWD-Pins liegen an der Unterkante des Moduls, direkt über dem Stecker.
Keine Strapping-, Flash- (26–32) oder PSRAM-Pins (33–37) werden benutzt.

### SWD-Stecker J3 (von links nach rechts, Oberseite)

| GND | RST | CLK | DIO | 3V3 |
|---|---|---|---|---|
| Masse | nRST / C45 | SWCLK | SWDIO | 3,3 V **vom Gerät** (schaltbar) – oder Messeingang, wenn die VCU anders versorgt wird |

> [!WARNING]
> Die 3V3-Leitung ist ein **Ausgang**. Hängt die VCU schon an Fahrakku oder
> Netzteil, schaltet die Firmware die eigene Versorgung **nicht** ein (sie misst
> die Spannung vorher). Trotzdem gilt wie beim ST-LINK: immer nur **eine**
> Stromquelle für die VCU.

### Bedienelemente

| Teil | Funktion |
|---|---|
| Schiebeschalter (rechts, „PWR") | Gerät ein/aus. Geladen wird auch im ausgeschalteten Zustand. |
| RESET (links) | ESP32 neu starten |
| BOOT (rechts) | beim Einstecken/Reset halten = Download-Modus (nur bei „verflashter" Firmware nötig) |
| LED „CHG" rot / grün | lädt / voll (TP4056) |
| LED „STAT" gelb | kurzes Blitzen alle 2 s = bereit, schnelles Blinken = Vorgang läuft |

---

## Akku

* **1S-LiPo 3,7 V mit JST-PH-2,0-Stecker**, z. B. Bauform **503450** (≈ 34 × 50 mm,
  ~1000 mAh) – passt auf die Rückseite. Laufzeit ca. 5–8 h WLAN-Betrieb.
* Ladestrom ist mit R4 = 3,3 kΩ auf ~360 mA eingestellt → Akku **≥ 400 mAh**.
  Für kleinere Akkus R4 vergrößern (4,7 kΩ ≈ 255 mA, 10 kΩ ≈ 120 mA).
* ⚠️ **Polarität prüfen!** Bei JST-PH-Akkus ist die Belegung nicht einheitlich.
  Auf der Platine: **„+" = Pin 1 = links**, „−" = rechts (siehe Aufdruck).
  Falsch herum zerstört den Lader. Notfalls die Crimpkontakte im Stecker umstecken.

---

## Bestellung bei JLCPCB (Platine + Bestückung)

Alle Dateien liegen fertig in [`production/`](production/):

| Datei | Wofür |
|---|---|
| `x3tuner-gerbers.zip` | Gerber + Bohrdaten → beim PCB-Upload |
| `x3tuner-bom.csv` | Stückliste mit LCSC-Nummern → bei „PCB Assembly" |
| `x3tuner-cpl.csv` | Bestückungspositionen → bei „PCB Assembly" |

1. Auf jlcpcb.com `x3tuner-gerbers.zip` hochladen. Standard-Einstellungen
   reichen: **2 Lagen, 1,6 mm, HASL bleifrei**, beliebige Lötstoppfarbe.
2. **PCB Assembly** aktivieren → *Economic*, **Top Side**.
3. BOM und CPL hochladen. Alle Teile sollten automatisch zugeordnet werden.
4. In der Bauteil-Vorschau **jede Drehung prüfen**, besonders die ICs
   (U2, U3, U4, U5, U6, Q1, Q2), die LEDs und J2. Das CPL enthält schon die
   üblichen JLC-Korrekturen für SOT-23 und SOIC – kontrolliere sie trotzdem in der Vorschau.
5. **Nicht bestückt** werden (bewusst, spart Geld): die **Stiftleiste J3**
   (normale gewinkelte 1×5-Stiftleiste 2,54 mm, selbst einlöten) und der Akku.

### Kosten (grobe Schätzung, Stand 2026, ohne Versand und Zoll)

| Posten | ca. |
|---|---|
| Bauteile pro Platine (davon ESP32-S3-N16R8 ≈ 4 $) | ≈ 5,50 $ |
| Platine 2 Lagen, 38 × 60 mm | ≈ 0,40–1 $ pro Stück |
| JLC-Bestückung: Einrichtung + Schablone | ≈ 10 $ pro Auftrag |
| „Extended"-Teile: Modul, DW01A, ME6211, USB-C, JST, Schalter (je ~3 $) | ≈ 18 $ pro Auftrag |
| **≈ pro Gerät bei 10 Stück** | **≈ 9–10 $** |
| **≈ pro Gerät bei 50 Stück** | **≈ 6–7 $** |
| + Akku (≈ 2–4 $) und Stiftleiste (≈ 0,10 $) | |

Kostenbewusste Teilewahl: TP4056, HJ8205, SRV05-4, AO3401A, B5819W, Taster,
alle Widerstände/Kondensatoren und rote/grüne LED sind JLC-„Basic"- oder
„Preferred"-Teile ohne Rüstgebühr.

---

## Vor der Bestellung prüfen

Ehrliche Liste, was in dieser Umgebung **nicht** direkt verifiziert werden konnte:

* **LCSC-Nummern** wurden über Sekundärquellen geprüft (JLC-Teile-Scrapes,
  KiCad/EasyEDA-Bibliotheken), nicht direkt auf lcsc.com. JLC zeigt beim
  Upload an, falls eine Nummer nicht passt oder nicht lieferbar ist.
* **HJ8205 (Q2) Pinbelegung** (1 = S1, 2 = D, 3 = S2, 4 = G2, 5 = D, 6 = G1)
  stammt aus zwei übereinstimmenden EasyEDA-Symbolen. Kurz mit dem Datenblatt
  abgleichen. Pin-kompatible Alternative: FS8205A im SOT-23-6 (C908265).
* **Drehungen im CPL** – siehe Schritt 4 oben.
* **Schiebeschalter**: welche Stellung „EIN" ist, hängt von der Einbaurichtung
  ab. Einfach ausprobieren; es ist nur mit „PWR" beschriftet.
* Die **Firmware** für `x3tuner` konnte hier nicht komplett gebaut werden, weil
  die PlatformIO-Registry blockiert war. Die neuen Dateien wurden mit dem
  Host-Compiler geprüft und die Board-Logik ist per Unit-Test abgedeckt.

---

## Inbetriebnahme

1. Akku anstecken (Polarität!), USB-C einstecken → rote LED = lädt.
2. Schalter auf EIN. Firmware flashen:
   ```bash
   pio run -e x3tuner -t upload
   ```
   Beim allerersten Mal ggf. **BOOT gedrückt halten und RESET drücken**, dann
   wird der ESP32-S3 als USB-Gerät für den Upload erkannt.
3. Mit dem WLAN **`x3utils-esp32`** (Passwort `x3utils123`) verbinden und
   **http://192.168.4.1/** öffnen. Die Karte „X3-Tuner" zeigt Akku, USB und die
   Spannung an der VCU.
4. SWD-Kabel an die VCU (GND, nRST/C45, SWCLK, SWDIO, 3V3).
   * VCU **ohne** Fahrakku: Button **„VCU power ON"** – das Gerät versorgt die VCU.
   * Modus **Power-race**: das Gerät schaltet die VCU selbst aus, lässt sie
     entladen und schaltet sie wieder ein, während es die Verbindung aufbaut.
     Den Stecker muss man dafür nicht mehr ziehen.
5. Wie gewohnt: **Check connection → Backup → erst dann flashen.**

Neu in der Firmware für diese Platine: `GET /api/status` liefert zusätzlich
`vbat`, `bat`, `usb`, `vtgt`, `tgtPower`; `POST /api/target {"on":true|false}`
schaltet die VCU-Versorgung.

---

## Dateien & Neu-Generieren

```
hardware/
├── gen/circuit.py        ← EINZIGE Quelle: Bauteile, Netze, Positionen, LCSC-Nummern
├── gen/make_sch.py       Schaltplan (.kicad_sch) + Projekt-Symbolbibliothek
├── gen/check_netlist.py  prüft die KiCad-Netzliste des Schaltplans gegen circuit.py
├── gen/make_pcb.py       Platine: Platzierung, USB-Vorverdrahtung, DSN/SES, GND-Flächen, Stitching
├── gen/drc.py            KiCad-DRC
├── gen/make_fab.py       Gerber/Bohrdaten, BOM, CPL, PDFs, Bilder
├── gen/build.sh          alles in einem Rutsch
├── kicad/                KiCad-7-Projekt (mit KiCad 7 oder neuer öffnen und bearbeiten)
├── production/           Fertigungsdaten für JLCPCB
└── docs/                 Schaltplan-PDF, Bestückungsplan, Renderings
```

Die KiCad-Dateien lassen sich ganz normal in KiCad öffnen und von Hand
weiterbearbeiten. Wer lieber am Generator ändert: `circuit.py` anpassen und
`gen/build.sh` laufen lassen. Dafür brauchst du KiCad 7 (`kicad-cli` und das Python-Modul `pcbnew`), Java 17+,
[Freerouting 1.9](https://github.com/freerouting/freerouting/releases) (`FREEROUTING=/pfad/zur.jar`),
`xvfb-run`, `rsvg-convert` und ImageMagick. Mit `SKIP_ROUTE=1` wird das
mitgelieferte Routing (`kicad/x3tuner.ses`) wiederverwendet.

Lizenz wie das Repository (MIT).
