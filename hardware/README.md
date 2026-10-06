# X3-Tuner – eigene Platine für x3utils-esp32

Ein **All-in-one-Gerät** für die AT32F415-VCU der X3-Scooter-Familie (ZT3 Pro,
Max G3, F3 / F3 Pro): ESP32-C3 (Spar-Version), eigener Akku mit Lade- und
Schutzschaltung, schaltbare 3,3-V-Versorgung für die VCU und ein SWD-Stecker.
Ersetzt **ST-LINK, PC und Kabelsalat** – bedient wird alles per Handy-Browser
über WLAN (Firmware: dieses Repository, Environment `x3tuner`).

| Oberseite | Unterseite |
|---|---|
| ![Oberseite](docs/pcb-top.png) | ![Unterseite](docs/pcb-bottom.png) |

[Schaltplan (PDF)](docs/x3tuner-schematic.pdf) ·
[Bestückungsplan (PDF)](docs/x3tuner-assembly.pdf) ·
[Fertigungsdaten](production/) ·
[3D-Druck-Gehäuse](case/)

> [!IMPORTANT]
> **Status: Design fertig (Rev. 1.1, Spar-Version mit ESP32-C3), noch nicht gefertigt.** Die Platine besteht den
> KiCad-DRC (0 Fehler, 0 offene Verbindungen) und der Schaltplan wird
> automatisch gegen die Netzliste geprüft – ein gebauter Prototyp existiert
> aber noch nicht. Bitte zuerst **2–5 Stück** bestellen und testen. Was du vor
> der Bestellung prüfen solltest, steht unter [Vor der Bestellung prüfen](#vor-der-bestellung-prüfen).

---

## Was drauf ist

| Block | Lösung | Warum |
|---|---|---|
| MCU | **ESP32-C3-WROOM-02-N4**: 4 MB Flash, 400 KB RAM, WLAN + BLE | ca. 1,20–1,55 $ günstiger als der S3; die Firmware braucht nur 128 KB Puffer |
| USB | USB-C direkt an GPIO18/19 (natives USB des C3) | kein CH340/CP2102 nötig → günstiger |
| Laden | **TP4056**, ca. 360 mA (R4 = 3,3 kΩ), LEDs rot = lädt, grün = voll | Standard, sehr billig |
| Akku-Schutz (BMS) | **DW01A + 8205-Dual-MOSFET** | Schutz vor Über- und Tiefentladung, Überstrom und Kurzschluss |
| Power-Path | P-MOSFET AO3401A + Schottky B5819W | mit USB läuft das Gerät aus USB, der Akku wird nur geladen |
| 3,3 V ESP | ME6211 (500 mA LDO), Ein/Aus-Schiebeschalter **MSK12C02** am Enable-Pin | kleiner Ruhestrom, Laden auch im ausgeschalteten Zustand; Schalter ca. 0,05 $ |
| 3,3 V VCU | **zweiter ME6211, per GPIO10 schaltbar**, mit Spannungsmessung | Firmware schaltet die VCU selbst ein → **automatischer Power-Race** |
| SWD | 1×5-Stiftleiste 2,54 mm (3V3 · DIO · CLK · RST · GND), 100 Ω Serienwiderstände | Dupont-Kabel wie beim ST-LINK |
| Bedienung | RESET, BOOT, Status-LED (gelb) | |
| Messung | Akkuspannung, USB vorhanden, Spannung an der VCU (alle ADC1) | Akkuanzeige in der Web-Oberfläche, Schutz gegen Doppelversorgung |

**Platine:** 38 × 54,5 mm, 2 Lagen, 1,6 mm, alle SMD-Teile auf der Oberseite
(einseitige Bestückung = günstig). Unten durchgehende Massefläche – dort klebt
der Akku. Antenne am oberen Rand, ohne Kupfer darunter.

### Pinbelegung ESP32-C3-WROOM-02

| GPIO | Funktion | | GPIO | Funktion |
|---|---|---|---|---|
| IO5 | SWCLK (über 100 Ω) | | IO3 | VTGT_SENSE (Spannung an der VCU, ½) |
| IO6 | SWDIO (über 100 Ω) | | IO1 | VBUS_SENSE (USB steckt, ½) |
| IO7 | nRST (zur VCU, über 100 Ω) | | IO4 | VBAT_SENSE (Akkuspannung, ½) |
| IO10 | TGT_EN (VCU-Versorgung ein) | | IO0 | Status-LED |
| IO9 | BOOT-Taste | | IO18/19 | USB D−/D+ |
| EN | RESET-Taste | | IO20/21 | UART0 (Testpads TP2/TP1) |
| IO2, IO8 | Strapping-Pins, je 10 kΩ nach 3,3 V | | | |

Die SWD-Pins liegen links am Modul, auf der Seite des Steckers. Alle
Messeingänge sind ADC1, denn ADC2 funktioniert beim C3 nicht, solange WLAN läuft.

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
| Schiebeschalter (links, „PWR") | Gerät ein/aus. Geladen wird auch im ausgeschalteten Zustand. |
| RESET (rechts) | ESP32 neu starten |
| BOOT (links) | beim Reset halten = Download-Modus (nur bei „verflashter" Firmware nötig) |
| LED „CHG" rot / grün | lädt / voll (TP4056) |
| LED „STAT" gelb | kurzes Blitzen alle 2 s = bereit, schnelles Blinken = Vorgang läuft |

---

## Akku

* **1S-LiPo 3,7 V mit JST-PH-2,0-Stecker**, Bauform **503040** (≈ 30 × 40 × 5 mm,
  ~600 mAh). Er passt unter die Platine und ins Gehäuse. Laufzeit ca. 4–6 h WLAN-Betrieb
  (der C3 braucht weniger Strom als der S3). Größer als 34 × 43 mm passt nicht
  mehr unter die 54,5-mm-Platine.
* Ladestrom ist mit R4 = 3,3 kΩ auf ~360 mA eingestellt → Akku **≥ 400 mAh**.
  Für kleinere Akkus R4 vergrößern (4,7 kΩ ≈ 255 mA, 10 kΩ ≈ 120 mA).
* ⚠️ **Polarität prüfen!** Bei JST-PH-Akkus ist die Belegung nicht einheitlich.
  Auf der Platine: **„+" = Pin 1 = links**, „−" = rechts (siehe Aufdruck).
  Falsch herum zerstört den Lader. Notfalls die Crimpkontakte im Stecker umstecken.

---

## Wo fertigen lassen? (Platine + Bestückung, Lieferung nach Deutschland)

Preisvergleich für die Spar-Version mit ESP32-C3 und MSK12C02, Stand Oktober 2026.
Gegenüber der ersten S3-Version spart das etwa 3 $ pro Platine. Werte sind **inklusive 19 % MwSt.** und
günstigstem Versand, Genauigkeit etwa ±25 %. Live-Preise im Warenkorb können
abweichen, vor allem beim ESP32-Modul, weil Speicherchips 2026 teurer geworden sind.

| Anbieter | 5 Stück | 10 Stück | 50 Stück | Anmerkung |
|---|---|---|---|---|
| **JLCPCB** (Economic PCBA) | **≈ 15 $/Stk.** | **≈ 10 $/Stk.** | **≈ 6 $/Stk.** | **Empfehlung.** Niedrigste Fixkosten, alle Teile ab Lager (LCSC), MwSt. wird an der Kasse erhoben |
| NextPCB („Rev0") | ≈ 12 $ | ≈ 9 $ | ≈ 5 $ | Nur die **erste** Bestellung (Bestückung gratis bis 500 $, Aktion bis 31.12.2026). Teilepreise und Versand nicht geprüft |
| PCBWay | ≈ 16 $ | ≈ 11 $ | ≈ 7–8 $ | 29 $ Einrichtung (Aktion), kauft Teile bei Digi-Key/Mouser |
| ALLPCB | ≈ 16 $ | ≈ 11 $ | – | 35 $ Einrichtung bis 10 Stück |
| AISLER (Deutschland) | ≈ 50 € | ≈ 30 € | ≈ 11 € | kein Zoll, aber 7,50 € je Bauteilsorte |

**Fazit:** Bei **JLCPCB** bestellen. Lohnt sich ein einmaliger Versuch, hol
zusätzlich ein Angebot bei **NextPCB** (Erstbestellungs-Aktion) mit
`x3tuner-bom-generic.csv` ein. Ein Akku (ca. 1,50–3 $) und die Stiftleiste (ca. 0,10 $)
kommen jeweils noch dazu.

So setzen sich die JLC-Kosten zusammen:
- **Einmal pro Auftrag:** 8 $ Einrichtung und 1,50 $ Schablone.
- **Pro „Extended"-Bauteilsorte:** 3 $. Laut einer Quelle seit 12/2025 nur noch 1,50 $, das zeigt dir der Warenkorb.
- **Diese 6 Extended-Sorten sind nötig:** ESP32-Modul, DW01A, ME6211, USB-C, JST-Buchse, Schalter.
- **Für keine davon** gibt es bei JLC derzeit einen gebührenfreien Ersatz. Das wurde gegen die aktuelle Basic/Preferred-Liste geprüft.
- **Der Rest ist schon gebührenfrei („Basic"/„Preferred"):** TP4056, HJ8205, SRV05-4, AO3401A, B5819W, Taster, LEDs und alle Widerstände und Kondensatoren.
- **Größter Kostenblock:** das Funkmodul. Der ESP32-C3-WROOM-02-N4 kostet ca. 2,45 $ ab 100 Stück, der ESP32-S3 mit 8 MB PSRAM ca. 3,63–4,00 $.

> [!NOTE]
> **Zoll seit 1. Juli 2026:** Auf Pakete bis 150 € kommt in der EU eine Zollgebühr von 3 € pro Warenposition.
> JLC und PCBWay erheben die MwSt. über IOSS direkt an der Kasse. Bei größeren
> Bestellungen (über 150 €) den **DDP**-Versand wählen, sonst kassiert der
> Paketdienst MwSt. und Gebühr (ca. 15 €) bei der Zustellung.

### Bestellen bei JLCPCB – Schritt für Schritt

Alle Dateien liegen fertig in [`production/`](production/):

| Datei | Wofür |
|---|---|
| `x3tuner-gerbers.zip` | Gerber + Bohrdaten → beim PCB-Upload |
| `x3tuner-bom.csv` | Stückliste mit LCSC-Nummern → bei „PCB Assembly" |
| `x3tuner-cpl.csv` | Bestückungspositionen → bei „PCB Assembly" |
| `x3tuner-bom-generic.csv` | herstellerneutrale Stückliste (Hersteller-Teilenummern) für NextPCB, PCBWay & Co. |

1. Auf jlcpcb.com `x3tuner-gerbers.zip` hochladen. Standard-Einstellungen
   reichen: **2 Lagen, 1,6 mm, HASL bleifrei**, beliebige Lötstoppfarbe.
2. **PCB Assembly** aktivieren → **Economic**, **Top Side**, Menge 5 oder 10.
3. BOM und CPL hochladen. Alle Teile sollten automatisch zugeordnet werden.
4. In der Bauteil-Vorschau **jede Drehung prüfen**, besonders die ICs
   (U2, U3, U4, U5, U6, Q1, Q2), die LEDs und J2. Das CPL enthält schon die
   üblichen JLC-Korrekturen für SOT-23 und SOIC – kontrolliere sie trotzdem in der Vorschau.
5. **Nicht bestückt** werden (bewusst, spart Geld): die **Stiftleiste J3**
   (normale gewinkelte 1×5-Stiftleiste 2,54 mm, selbst einlöten) und der Akku.
6. An der Kasse den **SMT-Gutschein** einlösen: Neukunden bekommen 10 $, außerdem
   gibt es jeden Monat 9 $, was die Einrichtungsgebühr deckt. Pro Auftrag gilt
   ein Gutschein.

---

## Größere Stückzahlen: 100–200 und 500 Stück

**Wichtig:** JLCs günstige *Economic*-Bestückung nimmt nur **2–50 Stück pro
Auftrag**. Die *Standard*-Bestückung verlangt mindestens 70 × 70 mm, die
Platine hat aber nur 38 × 54,5 mm. Deshalb gibt es einen fertigen **Nutzen
(Panel) mit 10 Platinen** in [`production/panel/`](production/panel/):

![Panel 5x2](docs/panel-top.png)

* 5 × 2 Platinen auf 202 × 128 mm, 3 mm gefräste Spalte, Abbrechstege mit
  Mouse-Bites, Randstreifen mit 3 Passermarken und 3 Werkzeugbohrungen.
* Die Stege sitzen bewusst **nicht** an USB-C, Schalter oder SWD-Stecker,
  damit nach dem Abbrechen kein Grat ins Gehäuse drückt.
* Die obere Reihe ist um 180° gedreht, so zeigen alle SWD-Kanten zu den Randstreifen.
* Bestellmenge in **Panels**: 100 Stück = 10, 200 Stück = 20, 500 Stück = 50
  Panels. Damit ist alles im Economic-Tarif, 500 ist genau das Maximum.
* Upload genau wie bei der Einzelplatine, nur mit `x3tuner-panel-gerbers.zip`,
  `x3tuner-panel-bom.csv` und `x3tuner-panel-cpl.csv`.
  Option „Panel by JLCPCB" **nicht** wählen, das Panel ist schon fertig.

### Kosten pro Platine (bestückt, ab Werk JLCPCB, Lieferung nach Deutschland)

Schätzung, Oktober 2026, ±20 %. Annahmen:
- **ESP32-C3-WROOM-02-N4:** 2,45 $ ab 100 Stück bei LCSC.
- **Übrige Teile:** ca. 0,65 $, der Schalter MSK12C02 kostet davon nur ca. 0,05 $.
- **Löten:** ca. 190 Lötstellen × 0,0016 $.
- **Fixkosten pro Auftrag:** 27,50 $.
- **Versand:** DHL Express.

| | 100 Stück | 200 Stück | 500 Stück |
|---|---|---|---|
| Bauteile | ≈ 3,10 $ | ≈ 3,10 $ | ≈ 3,08 $ |
| Bestückung (Lötstellen) | 0,30 $ | 0,30 $ | 0,30 $ |
| Fixkosten anteilig | 0,28 $ | 0,14 $ | 0,06 $ |
| Leiterplatte (Panels) | ≈ 0,28 $ | ≈ 0,23 $ | ≈ 0,18 $ |
| Versand + Verzollung | ≈ 0,42 $ | ≈ 0,28 $ | ≈ 0,18 $ |
| **Summe netto** | **≈ 4,40 $** | **≈ 4,05 $** | **≈ 3,80 $** |
| **inkl. 19 % Einfuhr-USt.** | **≈ 5,20 $** | **≈ 4,80 $** | **≈ 4,50 $** |
| **Gesamtbetrag** | **≈ 520 $** | **≈ 965 $** | **≈ 2.260 $** |

Zum Vergleich die erste Version mit ESP32-S3 (8 MB PSRAM) und C&K-Schalter:
≈ 7,50 / 7,10 / 6,80 $ pro Platine. Die Spar-Version kostet also rund **30 % weniger**.

Über 150 € Warenwert gilt die normale Einfuhr: 19 % Einfuhrumsatzsteuer, für
Firmen als Vorsteuer erstattbar, plus Verzollungsgebühr des Paketdiensts.
Für bestückte Leiterplatten fällt in der Regel kein Zoll an. **DDP**-Versand
wählen, dann ist alles vorab bezahlt.

### Komplettgerät (Platine + Akku + Gehäuse)

| Posten | 100–200 Stück | 500 Stück |
|---|---|---|
| Platine bestückt (inkl. USt.) | ≈ 4,80–5,20 $ | ≈ 4,50 $ |
| Akku 503040 (≈ 600 mAh) mit JST-PH | ≈ 1,50–2,50 $ (Herstellerangebot einholen) | ≈ 1,50–2 $ |
| Stiftleiste 1×5 gewinkelt | ≈ 0,05 $ | ≈ 0,03 $ |
| Gehäuse | selbst gedruckt ≈ 0,30 € Material, aber 1,5–2 h Druckzeit pro Stück | Druckdienst oder Druckfarm, ca. 2–4 $ (Angebot einholen) |
| **≈ Material pro Gerät** | **≈ 6,50–8 $** | **≈ 8–10,50 $** mit Druckdienst, selbst gedruckt ≈ 6,50 $ |

Dazu kommen pro Gerät ca. 5–8 Minuten Handarbeit: Stiftleiste löten, Firmware
flashen, testen, Akku einlegen, Deckel aufklicken. Ein Spritzguss-Gehäuse
(Werkzeug ca. 3.000–8.000 €) lohnt sich erst ab einigen tausend Stück.

> [!IMPORTANT]
> **Wenn du die Geräte verkaufen willst**, brauchst du in Deutschland/EU vorher:
> - eine CE-Konformitätserklärung nach Funkanlagen-Richtlinie (RED), EMV und RoHS. Die
>   Zertifikate des ESP32-Moduls helfen, ersetzen sie aber nicht.
> - eine **WEEE-Registrierung** bei der stiftung ear.
> - eine Akku-Registrierung nach Batterierecht.
> - eine Verpackungsregistrierung (LUCID).
>
> Lithium-Akkus brauchen beim Versand UN38.3-Unterlagen. Außerdem verliert ein
> getunter E-Scooter in Deutschland auf öffentlichen Straßen seine
> Betriebserlaubnis (eKFV) und den Versicherungsschutz. Ein Gerät, das als
> „Tuning"-Werkzeug beworben wird, kann deshalb rechtliche Risiken bringen.
> Kläre das vor einem Verkauf ab.

---

## Gehäuse

Ein passendes, schraubenloses **3D-Druck-Gehäuse** inklusive Akkufach liegt in
[`case/`](case/). Es ist facettiert im „Stick"-Look, ca. **42 × 68 × 17 mm** groß
und hat Lichtschlitze, Pin-Löcher für RESET/BOOT und eine gravierte SWD-Belegung.
Druck- und Montageanleitung stehen in [`case/README.md`](case/README.md).

| Zusammengebaut | Durchsichtig (Aufbau) | Schnitt |
|---|---|---|
| ![Gehäuse](docs/case-assembly.png) | ![Röntgenansicht](docs/case-xray.png) | ![Schnitt](docs/case-section.png) |

---

## Vor der Bestellung prüfen

Ehrliche Liste, was in dieser Umgebung **nicht** direkt verifiziert werden konnte:

* **LCSC-Nummern** wurden über Sekundärquellen geprüft (JLC-Teile-Scrapes,
  KiCad/EasyEDA-Bibliotheken), nicht direkt auf lcsc.com. JLC zeigt beim
  Upload an, falls eine Nummer nicht passt oder nicht lieferbar ist.
* **HJ8205 (Q2) Pinbelegung** (1 = S1, 2 = D, 3 = S2, 4 = G2, 5 = D, 6 = G1)
  stammt aus zwei übereinstimmenden EasyEDA-Symbolen. Kurz mit dem Datenblatt
  abgleichen. Pin-kompatible Alternative: FS8205A im SOT-23-6 (C908265).
* **ESP32-C3-WROOM-02 Pinbelegung:**
  - 1 3V3, 2 EN, 3–8 IO4–IO9, 9 GND
  - 10 IO10, 11 RXD, 12 TXD, 13 IO18, 14 IO19
  - 15 IO3, 16 IO2, 17 IO1, 18 IO0, 19 EPAD/GND

  Die Belegung stammt aus dem Espressif-Datenblatt, wurde hier aber nicht noch einmal gegengelesen.
  Der Footprint kommt aus der KiCad-Bibliothek. Kurz mit dem Datenblatt abgleichen.
* **Schiebeschalter MSK12C02 (C431540):** Den Land-Pattern habe ich nach dem
  EasyEDA-Footprint gezeichnet, den JLC selbst für C431540 verwendet. Ein Datenblatt war nicht erreichbar.
  Prüfe in der JLC-Vorschau, ob der Schalter auf den Pads sitzt. Der Hebel steht nur
  ca. 1 mm über den Platinenrand hinaus, im Gehäuse bedienst du ihn mit dem Fingernagel in der Griffmulde.
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
   Wird kein Port gefunden: **BOOT gedrückt halten und RESET drücken**, dann
   meldet sich der ESP32-C3 als USB-Gerät für den Upload.
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
├── gen/make_case.sh      Gehäuse: Positionen aus circuit.py → STL, Renderings, Maßblatt (OpenSCAD)
├── kicad/                KiCad-7-Projekt (mit KiCad 7 oder neuer öffnen und bearbeiten)
├── gen/make_panel.py     10er-Nutzen für Serien (KiKit; KIKIT=/pfad/zu/kikit)
├── production/           Fertigungsdaten (JLCPCB + herstellerneutrale Stückliste)
│   └── panel/            Fertigungsdaten für den 10er-Nutzen (100–500 Stück)
├── case/                 3D-Druck-Gehäuse (OpenSCAD + STL)
└── docs/                 Schaltplan-PDF, Bestückungsplan, Renderings
```

Die KiCad-Dateien lassen sich ganz normal in KiCad öffnen und von Hand
weiterbearbeiten. Wer lieber am Generator ändert: `circuit.py` anpassen und
`gen/build.sh` laufen lassen. Dafür brauchst du KiCad 7 (`kicad-cli` und das Python-Modul `pcbnew`), Java 17+,
[Freerouting 1.9](https://github.com/freerouting/freerouting/releases) (`FREEROUTING=/pfad/zur.jar`),
`xvfb-run`, `rsvg-convert` und ImageMagick. Mit `SKIP_ROUTE=1` wird das
mitgelieferte Routing (`kicad/x3tuner.ses`) wiederverwendet.

Lizenz wie das Repository (MIT).
