# X3-Tuner Mini – Trägerplatine für das ESP32-C3 SuperMini

Die günstige Variante des X3-Tuners, als schmaler **Stick** mit 3D-Druck-Gehäuse
(ca. 78 × 24 × 22 mm). Den ESP32 kaufst du als fertiges **ESP32-C3 SuperMini**
(ca. 1,80 €, mit bereits eingelöteten Stiften) und **steckst ihn einfach auf**.
Die Trägerplatine bringt alles mit, was dem SuperMini fehlt:

- 1S-LiPo-Akku mit TP4056-Ladeschaltung, geladen über die USB-C-Buchse des SuperMini
- Verpolschutz für den Akku (viele Billig-Akkus haben vertauschte Kabel)
- Ein/Aus-Schiebeschalter
- schaltbare 3,3-V-Versorgung für die Scooter-VCU (Power-Race per Firmware)
- Messung von Akku, USB und VCU-Spannung
- SWD-Stiftleiste zum Scooter

**Gelötet wird nichts.** Die Fabrik bestückt alle Teile, auch die beiden
Buchsenleisten und die Stiftleiste.

| Gehäuse | Durchsichtig (Aufbau) |
|---|---|
| ![Gehäuse](docs/case-assembly.png) | ![Röntgenansicht](docs/case-xray.png) |
| **Schnitt** | **Explosionsansicht** |
| ![Schnitt](docs/case-section.png) | ![Explosionsansicht](docs/case-exploded.png) |

| Platine oben | Platine unten |
|---|---|
| ![Oberseite](docs/pcb-top.png) | ![Unterseite](docs/pcb-bottom.png) |

[Schaltplan (PDF)](docs/x3carrier-schematic.pdf) ·
[Bestückungsplan (PDF)](docs/x3carrier-assembly.pdf) ·
[Fertigungsdaten](production/) ·
[Gehäuse (STL)](case/stl/)

> [!IMPORTANT]
> **Status: Design fertig (Rev. 1.1, Stick-Form), noch nicht gefertigt.** DRC:
> 0 Fehler, 0 offene Verbindungen, der Schaltplan wird automatisch gegen die
> Netzliste geprüft. Das Gehäuse ist gegen Platine, SuperMini und Akku auf
> Kollisionen geprüft. Vor der Bestellung bitte [diese Punkte](#vor-der-bestellung-prüfen) prüfen.

## Was drauf ist

| Block | Lösung |
|---|---|
| Platine | 20,5 × 65 mm, 2 Lagen, alle Teile oben |
| ESP32 | ESP32-C3 SuperMini, aufgesteckt in 2 × 1×8-Buchsenleisten (2,54 mm, 8,5 mm hoch), USB-C an der vorderen Kante |
| Laden | TP4056, ca. 235 mA, gespeist aus dem 5V-Pin des SuperMini (= USB VBUS). LEDs: rot = lädt, grün = voll |
| Akku | 1S LiPo **mit eigener Schutzschaltung**, JST-PH-2.0-Buchse, Verpolschutz (P-MOSFET Q3) |
| Ein/Aus | Schiebeschalter MSK12C02. Er schaltet nur das Gate des P-MOSFET Q1 und trägt keinen Laststrom |
| Akkubetrieb | Akku → Q3 → Q1 → Schottky-Diode D1 → 5V-Pin → 3,3-V-Regler des SuperMini |
| VCU-Versorgung | P-MOSFET Q2 aus 3V3 des SuperMini, GPIO7 low = an, beim Booten aus |
| SWD | gewinkelte 1×5-Stiftleiste an der hinteren Kante (3V3 · DIO · CLK · RST · GND), 100 Ω Serienwiderstände |

### Belegung des SuperMini

Ansicht von oben, USB-C nach oben. Pin 1 jeder Reihe ist der Pin neben USB-C.
Auf der Platine zeigt USB-C zur vorderen Kante (Aufdruck „USB-C“), die
5V-Reihe liegt dann links (Aufdruck „5V“).

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
- **Akku:** Schalter auf EIN, dann versorgt der Akku das SuperMini über Q3, Q1 und D1.
  Durch die Diode und den Regler des SuperMini sinkt die 3,3-V-Schiene ab etwa
  3,5 V Akkuspannung. Das Gerät geht dann früher aus als mit einem eigenen
  Regler, nutzbar sind ca. 85–90 % der Akkukapazität.
- **Aus:** Am Akku hängt nur der Messteiler mit 1 MΩ + 1 MΩ, das sind ca. 2 µA.
- **Akku verkehrt herum:** Q3 sperrt. Es geht nichts kaputt, das Gerät läuft
  nur nicht mit Akku und lädt ihn nicht.

## Akku

Ins Gehäuse passt ein Akku bis **21 × 33 × 9,5 mm**. Er liegt in einer Tasche
unter dem Deckel, über der Ladeschaltung. Gut passen die Größen 802030,
702030 und 602030. Die Zahl steht für Dicke, Breite und Länge: 802030 ist
8,0 × 20 × 30 mm. Der Akku braucht
eine **Schutzschaltung** und einen **JST-PH-2.0-Stecker** (2 mm Raster). Beides
ist bei Akkus mit Stecker üblich.

| Akku | Kapazität | Maße (L × B × D) | Polarität | Preis |
|---|---|---|---|---|
| [PowerCells 802030](https://powercells.de/lipo-400mah-3-7v-akku-battery-3-6v-akku-jst-ph-2-0-lithium-ion-polymer.html?language=en) (empfohlen) | 400 mAh | 31 × 20 × 8 mm | nicht angegeben, prüfen | ca. 4 € |
| [efaso 702030](https://www.amazon.de/dp/B0BK9JQY42) (Amazon.de) | 300 mAh | 30 × 20 × 7 mm | nicht angegeben, prüfen | ca. 9 € |
| [Pimoroni LiPo 150 mAh](https://botland.store/battery-li-pol-1s-37-v/21461-li-pol-battery-pimoroni-150mah-37v-jst-connector-27x205x43mm-0704256796549.html) | 150 mAh | 27 × 20,5 × 4,3 mm | passt garantiert (Adafruit-Belegung) | ca. 6 € |
| [Berrybase LP-402025](https://www.berrybase.de/en/lp-402025-lithium-polymer-lipo-battery-3.7v-150mah-with-2-pin-jst-connector) | 150 mAh | 26 × 20 × 4 mm | nicht angegeben, prüfen | ca. 3,30 € |

Mit 400 mAh läuft das Gerät mit WLAN ca. 3–4 Stunden, mit 150 mAh gut eine
Stunde. Für einen Flash-Vorgang reicht beides. Der Ladestrom von ca. 235 mA
passt gut zu 300 und 400 mAh. Für die 150-mAh-Akkus ist er etwas hoch (1,5C),
sie altern dadurch schneller.

**Zwei kleine Akkus parallel** sind keine gute Idee: Sind sie beim Zusammenstecken
unterschiedlich voll, fließt ein großer Ausgleichsstrom, den nichts begrenzt.
Außerdem bräuchtest du ein Y-Kabel, und das müsste man löten. Ein einzelner
802030 hat mehr Kapazität als zwei 150-mAh-Zellen und passt in dasselbe Fach.

**Polarität:** Die Platine hat die Belegung von Adafruit und SparkFun:
**+ (rot) an Pin 1**. Schau in die Öffnung der Buchse, die Platine liegt unten.
Dann ist + **links**, daneben steht „+“ auf der Platine. Am Akkustecker gilt:
Schau auf die Kontaktöffnungen, die Rastnase zeigt nach oben. Dann muss Rot
**rechts** sein. Bei Akkus von Amazon und AliExpress ist das oft vertauscht.
Steckst du so einen Akku an, sperrt der Verpolschutz und es passiert nichts.
Umbauen geht auch ohne Löten: Hebe mit einer Nadel die kleine Rastzunge über
einem Kontakt im Steckergehäuse an. Dann kannst du das Kabel samt Kontakt
herausziehen. Beide Kabel tauschen und wieder einrasten.

## Gehäuse

Facettierter Stick aus zwei Teilen, die ohne Schrauben einrasten.
Außenmaß **77,7 × 24,4 × 22,4 mm**. Es nutzt dasselbe Modell wie das
[X3-Tuner-Gehäuse](../case/) ([`../case/case_core.scad`](../case/case_core.scad)).

![Ansichten mit Maßen](docs/case-views.png)

| Ebene | Höhe |
|---|---|
| Boden | 1,2 mm |
| Luft für die Lötstellen der Buchsenleisten | 1,8 mm |
| Platine | 1,6 mm |
| SuperMini auf den Sockeln (11 mm), Platine des SuperMini (1 mm), USB-C (3,3 mm), Luft | 16,4 mm |
| Deckel | 1,4 mm |
| **Gesamt** | **22,4 mm** |

Flacher geht es mit einem aufgesteckten SuperMini nicht: Sockel, SuperMini und
USB-C sind zusammen schon gut 15 mm hoch.

- **Vorne:** USB-C in der Stirnseite, mit Vertiefung für den Kabelstecker.
- **Hinten:** SWD-Port. Ein 5-poliges Dupont-Buchsengehäuse wird durch den
  Schlitz auf die Stiftleiste gesteckt. Die Belegung steht über dem Schlitz.
- **Links:** Ein/Aus-Schieber mit Griffmulde.
- **Oben:** ein Lichtschlitz für die Lade-LED. Zwei Fenster über dem
  SuperMini zeigen seine rote und blaue LED. Durch die Fenster erreichst du
  voraussichtlich auch BOOT und RESET, zum Beispiel mit einem Zahnstocher.
- **Halt:** Zwei Stege im Deckel drücken auf die Stiftreihen des SuperMini,
  so kann es nicht aus den Sockeln rutschen. Ein dritter Steg drückt hinten
  auf die SWD-Leiste. Dazu kommen drei Rastnasen je Seite.

| Datei | Inhalt |
|---|---|
| `case/stl/x3mini-case-bottom.stl` | Unterschale: Auflagen für die Platine, Rastrand, Logo-Gravur |
| `case/stl/x3mini-case-lid.stl` | Deckel: Akkutasche, Stege, Fenster, Lichtschlitz |
| `case/stl/x3mini-case-print.stl` | beide Teile druckfertig auf einer Platte (Deckel liegt kopfüber) |
| `case/x3mini_case.scad` | OpenSCAD-Datei für dieses Gehäuse |
| `case/board_data.scad` | Positionen, automatisch erzeugt aus `gen/circuit_carrier.py` |

**Drucken:** PLA oder PETG, 0,2 mm Schichthöhe, ohne Stützen. Die Unterschale
liegt mit dem Boden auf dem Druckbett, der Deckel mit der Oberseite.

**Zusammenbau:**

1. SuperMini aufstecken: USB-C zur vorderen Kante (Aufdruck „USB-C“).
2. Platine in die Unterschale legen, die SWD-Stiftleiste zeigt zum Schlitz.
3. Akku einstecken (**Polarität prüfen**, siehe oben). Den Akku mit
   doppelseitigem Klebeband in die Tasche im Deckel kleben, das Kabel nach vorne.
4. Deckel aufsetzen. Das Kabel liegt dabei im Spalt zwischen SuperMini und Akku.
   Dann den Deckel einrasten lassen.

## Kosten

Bauteilpreise live von jlcpcb.com (6.10.2026), Gebühren laut JLC-Hilfe,
Versand „Global Standard Direct Line" 6,41 $. Alle Teile werden bestückt.

| JLCPCB, Economic | 2 Stück | 5 Stück |
|---|---|---|
| Bauteile | 4,97 $ | 8,25 $ |
| Einrichtung + Schablone | 9,71 $ | 9,71 $ |
| Extended-Gebühr: 5 Sorten × 3 $ (Buchsenleiste, TP4056, JST, Schalter, Stiftleiste) | 15,00 $ | 15,00 $ |
| Handlöten der Buchsen- und Stiftleisten (pro Auftrag) | 3,58 $ | 3,58 $ |
| Lötstellen | 0,23 $ | 0,58 $ |
| Platine + Versand | 10,41 $ | 10,41 $ |
| **Gesamt inkl. 19 % MwSt.** | **≈ 45 €** | **≈ 49 €** |
| **plus SuperMini à 1,80 €** | **≈ 48 €** | **≈ 58 €** |

Akku (ca. 4 €) und Gehäuse-Filament (ca. 12 g) kommen pro Gerät dazu.

**In Serie** wird es deutlich billiger: Mit dem 10er-Nutzen kostet ein
fertiges Gerät inklusive SuperMini ca. **3,75 €** bei 100 Stück und ca.
**3,15 €** bei 500 Stück. Akku und Gehäuse kommen noch dazu. Zum Vergleich: Die
X3-Tuner-Platine mit fest verlötetem Funkmodul kostet ca. 5,40 € pro Stück.

**Erste Bestellung über NextPCB „Rev 0":** Bestückung gratis, Platine 0,10 $
(Bedingungen siehe [`../README.md`](../README.md#am-günstigsten-für-die-erste-bestellung-nextpcb-rev-0)).
NextPCB verlangt mindestens 50 × 50 mm. Deshalb liegt in
[`production/nextpcb/`](production/nextpcb/) eine Variante mit 12 mm breiten
Randstreifen (50,6 × 65 mm), die man nach dem Bestücken abbricht. Kosten:

- Bauteile für 5 Stück: ca. 5–6 $.
- Versand: 10–20 $, den genauen Preis zeigt NextPCB erst im Konto.
- Zusammen mit 5 SuperMinis rechne ich mit **ca. 25–35 € für 5 komplette Geräte**.

## Bestellen

| Wo | Dateien |
|---|---|
| JLCPCB, 2–50 Stück | `production/x3carrier-gerbers.zip`, `x3carrier-bom.csv`, `x3carrier-cpl.csv` |
| JLCPCB, 100–500 Stück (10er-Nutzen, 114,6 × 149,1 mm) | `production/panel/x3carrier-panel-*` (Menge in Panels) |
| NextPCB „Rev 0" (erste Bestellung) | `production/nextpcb/x3carrier-nextpcb-*` (BOM mit Hersteller-Teilenummern) |
| andere Anbieter | `production/x3carrier-bom-generic.csv` |

Bei JLC: **Economic**, nur Oberseite, keine Extras. In der Vorschau prüfen:

- Die Pins der SWD-Stiftleiste J4 zeigen über die hintere Kante hinaus.
- Die Buchsenleisten J1/J2 sitzen auf ihren Pads.

## Vor der Bestellung prüfen

- **Dein SuperMini:** Vergleiche die Pinbeschriftung auf deinem Board mit der
  Tabelle oben. Es gibt Varianten (z. B. „SuperMini Plus" mit 2 × 7 Pins), die
  **nicht** passen.
  - Der Reihenabstand ist mit 15,24 mm (600 mil) angenommen. Miss ihn kurz nach.
  - Der erste Pin liegt laut meiner Annahme ca. 3,4 mm von der USB-Kante. Das
    bestimmt, wie weit die USB-C-Buchse vor der Platine steht. Im Gehäuse sind
    vorne 0,45 mm Luft.
  - Die Lage von BOOT, RESET und den LEDs ist geschätzt. Die Fenster im Deckel
    sind deshalb großzügig.
- **Aufstecken:** USB-C zeigt zur vorderen Platinenkante, die Aufschrift
  „USB-C“ und „5V“ auf der Platine zeigen die Lage. Wird das SuperMini verkehrt
  herum aufgesteckt, liegen 5 V auf einem GPIO.
- **Akku:** Nur einen 1S-LiPo **mit Schutzschaltung** verwenden. Polarität
  siehe [Akku](#akku).
- **VCU-Versorgung:** Ist das Gerät aus und die VCU extern versorgt, kann über
  die Body-Diode von Q2 ein kleiner Strom in die 3V3-Schiene fließen. Das ist
  harmlos, und die Firmware schaltet ohnehin nie gegen eine extern versorgte VCU.
- **Funk:** Die Antenne des SuperMini sitzt an seinem hinteren Ende. Unter ihr
  ist auf der Trägerplatine keine Kupferfläche, zum Akku sind es ca. 7 mm.

## Neu generieren

Die Trägerplatine nutzt denselben Generator wie der X3-Tuner
([`../gen/`](../gen/)), ausgewählt über `X3_CIRCUIT`:

```bash
cd hardware/gen
export X3_CIRCUIT=circuit_carrier     # Quelle: gen/circuit_carrier.py
./build.sh                            # Schaltplan, Platine, Routing, DRC, BOM/CPL
KIKIT=/pfad/zu/kikit python3 make_panel.py     # 10er-Nutzen
KIKIT=/pfad/zu/kikit python3 make_nextpcb.py   # Variante mit Randstreifen
./make_case.sh                        # Gehäuse: board_data.scad, STL, Bilder
```
