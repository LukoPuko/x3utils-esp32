# X3-Tuner Mini – Trägerplatine für das ESP32-C3 SuperMini

Die günstige Variante des X3-Tuners. Den ESP32 kaufst du als fertiges
**ESP32-C3 SuperMini** (ca. 1,80 €, mit bereits eingelöteten Stiften) und
**steckst ihn einfach auf**. Die Trägerplatine bringt alles mit, was dem
SuperMini fehlt:

- 1S-LiPo-Akku mit TP4056-Ladeschaltung, geladen über die USB-C-Buchse des SuperMini
- Ein/Aus-Schiebeschalter
- schaltbare 3,3-V-Versorgung für die Scooter-VCU (Power-Race per Firmware)
- Messung von Akku, USB und VCU-Spannung
- SWD-Stiftleiste zum Scooter

**Gelötet wird nichts.** Die Fabrik bestückt alle Teile, auch die beiden
Buchsenleisten und die Stiftleiste.

| Oberseite | Unterseite |
|---|---|
| ![Oberseite](docs/pcb-top.png) | ![Unterseite](docs/pcb-bottom.png) |

[Schaltplan (PDF)](docs/x3carrier-schematic.pdf) ·
[Bestückungsplan (PDF)](docs/x3carrier-assembly.pdf) ·
[Fertigungsdaten](production/)

> [!IMPORTANT]
> **Status: Design fertig (Rev. 1.0), noch nicht gefertigt.** DRC: 0 Fehler,
> 0 offene Verbindungen, der Schaltplan wird automatisch gegen die Netzliste
> geprüft. Vor der Bestellung bitte [diese Punkte](#vor-der-bestellung-prüfen) prüfen.

## Was drauf ist

| Block | Lösung |
|---|---|
| Platine | 38 × 50 mm, 2 Lagen, alle Teile oben |
| ESP32 | ESP32-C3 SuperMini, aufgesteckt in 2 × 1×8-Buchsenleisten (2,54 mm, 8,5 mm hoch) |
| Laden | TP4056, ca. 360 mA, gespeist aus dem 5V-Pin des SuperMini (= USB VBUS). LEDs: rot = lädt, grün = voll |
| Akku | 1S LiPo **mit eigener Schutzschaltung**, JST-PH-2.0-Buchse |
| Ein/Aus | Schiebeschalter MSK12C02. Er schaltet nur das Gate des P-MOSFET Q1 und trägt keinen Laststrom |
| Akkubetrieb | Akku → Q1 → Schottky-Diode D1 → 5V-Pin → 3,3-V-Regler des SuperMini |
| VCU-Versorgung | P-MOSFET Q2 aus 3V3 des SuperMini, GPIO7 low = an, beim Booten aus |
| SWD | gewinkelte 1×5-Stiftleiste (3V3 · DIO · CLK · RST · GND), 100 Ω Serienwiderstände |

### Belegung des SuperMini

Ansicht von oben, USB-C nach oben. Pin 1 jeder Reihe ist der Pin neben USB-C.

| Linke Reihe | Funktion | Rechte Reihe | Funktion |
|---|---|---|---|
| 5V | Akku / Lader (= USB VBUS) | GPIO5 | SWDIO |
| GND | GND | GPIO6 | nRST |
| 3V3 | 3,3 V für die VCU | GPIO7 | VCU-Versorgung ein (low) |
| GPIO4 | SWCLK | GPIO8 | blaue LED des SuperMini (Status) |
| GPIO3 | VCU-Spannung messen | GPIO9 | BOOT-Taster des SuperMini |
| GPIO2 | frei (Strapping) | GPIO10 | frei |
| GPIO1 | USB-Erkennung | GPIO20 | frei |
| GPIO0 | Akkuspannung messen | GPIO21 | frei |

SWD liegt auf denselben Pins wie beim nackten SuperMini (Firmware-Umgebung
`esp32-c3`). Die Trägerplatine hat ein eigenes Firmware-Profil:

```bash
pio run -e x3carrier -t upload
```

### Stromversorgung

- **USB eingesteckt:** USB versorgt das SuperMini, der TP4056 lädt den Akku.
  D1 sperrt, deshalb wird der Akku nur geladen und nicht gleichzeitig belastet.
  Laden funktioniert auch bei ausgeschaltetem Schalter. Das SuperMini läuft dann
  über USB trotzdem.
- **Akku:** Schalter auf EIN, dann versorgt der Akku das SuperMini über Q1 und D1.
  Durch die Diode und den Regler des SuperMini sinkt die 3,3-V-Schiene ab etwa
  3,5 V Akkuspannung. Das Gerät geht dann früher aus als mit einem eigenen
  Regler, nutzbar sind ca. 85–90 % der Akkukapazität.
- **Aus:** Am Akku hängt nur der Messteiler mit 1 MΩ + 1 MΩ, das sind ca. 2 µA.

## Kosten

Bauteilpreise live von jlcpcb.com (6.10.2026), Gebühren laut JLC-Hilfe,
Versand „Global Standard Direct Line" 6,41 $. Alle Teile werden bestückt.

| JLCPCB, Economic | 2 Stück | 5 Stück |
|---|---|---|
| Bauteile | 4,93 $ | 8,15 $ |
| Einrichtung + Schablone | 9,71 $ | 9,71 $ |
| Extended-Gebühr: 5 Sorten × 3 $ (Buchsenleiste, TP4056, JST, Schalter, Stiftleiste) | 15,00 $ | 15,00 $ |
| Handlöten der Buchsen- und Stiftleisten (pro Auftrag) | 3,58 $ | 3,58 $ |
| Lötstellen | 0,22 $ | 0,56 $ |
| Platine + Versand | 10,41 $ | 10,41 $ |
| **Gesamt inkl. 19 % MwSt.** | **≈ 45 €** | **≈ 49 €** |
| **plus SuperMini à 1,80 €** | **≈ 48 €** | **≈ 58 €** |

**In Serie** wird es deutlich billiger: Mit dem 10er-Nutzen kostet ein
fertiges Gerät inklusive SuperMini ca. **3,75 €** bei 100 Stück und ca.
**3,15 €** bei 500 Stück. Akku und Gehäuse kommen noch dazu. Zum Vergleich: Die
X3-Tuner-Platine mit fest verlötetem Funkmodul kostet ca. 5,40 € pro Stück.

**Erste Bestellung über NextPCB „Rev 0":** Bestückung gratis, Platine 0,10 $
(Bedingungen siehe [`../README.md`](../README.md#am-günstigsten-für-die-erste-bestellung-nextpcb-rev-0)).
Die Variante mit Randstreifen (52 × 50 mm) liegt in
[`production/nextpcb/`](production/nextpcb/). Kosten:

- Bauteile für 5 Stück: ca. 5–6 $.
- Versand: 10–20 $, den genauen Preis zeigt NextPCB erst im Konto.
- Zusammen mit 5 SuperMinis rechne ich mit **ca. 25–35 € für 5 komplette Geräte**.

## Bestellen

| Wo | Dateien |
|---|---|
| JLCPCB, 2–50 Stück | `production/x3carrier-gerbers.zip`, `x3carrier-bom.csv`, `x3carrier-cpl.csv` |
| JLCPCB, 100–500 Stück (10er-Nutzen) | `production/panel/x3carrier-panel-*` (Menge in Panels) |
| NextPCB „Rev 0" (erste Bestellung) | `production/nextpcb/x3carrier-nextpcb-*` (BOM mit Hersteller-Teilenummern) |
| andere Anbieter | `production/x3carrier-bom-generic.csv` |

Bei JLC: **Economic**, nur Oberseite, keine Extras. In der Vorschau prüfen:

- Die Pins der SWD-Stiftleiste J4 zeigen über die untere Kante hinaus.
- Die Buchsenleisten J1/J2 sitzen auf ihren Pads.

## Vor der Bestellung prüfen

- **Dein SuperMini:** Vergleiche die Pinbeschriftung auf deinem Board mit der
  Tabelle oben. Es gibt Varianten (z. B. „SuperMini Plus" mit 2 × 7 Pins), die
  **nicht** passen.
  - Der Reihenabstand ist mit 15,24 mm (600 mil) angenommen. Miss ihn kurz nach.
  - Der erste Pin liegt laut meiner Annahme ca. 3,4 mm von der USB-Kante. Das
    bestimmt nur, wie weit die USB-C-Buchse über die rechte Kante ragt.
- **Aufstecken:** USB-C zeigt zur rechten Platinenkante, die Aufschrift
  „USB-C ->" und „5V" auf der Platine zeigen die Lage. Wird es verkehrt herum
  aufgesteckt, liegen 5 V auf einem GPIO.
- **Akku:** Nur einen 1S-LiPo **mit Schutzschaltung** verwenden (bei Akkus mit
  JST-Stecker üblich). Prüfe die **Polarität**: + = Pin 1, links. Viele
  Händler-Kabel sind vertauscht.
- **VCU-Versorgung:** Ist das Gerät aus und die VCU extern versorgt, kann über
  die Body-Diode von Q2 ein kleiner Strom in die 3V3-Schiene fließen. Das ist
  harmlos, und die Firmware schaltet ohnehin nie gegen eine extern versorgte VCU.
- **Gehäuse:** Das Gehäuse in [`../case/`](../case/) passt noch nicht.
  Das SuperMini sitzt ca. 12 mm höher als die Bauteile auf der X3-Tuner-Platine.

## Neu generieren

Die Trägerplatine nutzt denselben Generator wie der X3-Tuner
([`../gen/`](../gen/)), ausgewählt über `X3_CIRCUIT`:

```bash
cd hardware/gen
export X3_CIRCUIT=circuit_carrier     # Quelle: gen/circuit_carrier.py
./build.sh                            # Schaltplan, Platine, Routing, DRC, BOM/CPL
KIKIT=/pfad/zu/kikit python3 make_panel.py     # 10er-Nutzen
KIKIT=/pfad/zu/kikit python3 make_nextpcb.py   # Variante mit Randstreifen
```
