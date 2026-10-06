# X3-Tuner Gehäuse (3D-Druck)

Zweiteiliges Rast-Gehäuse für die X3-Tuner-Platine **plus Akku**, ohne
Schrauben. Außenmaß **ca. 42 × 65 × 17 mm**.

| Zusammengebaut | Explosionsansicht |
|---|---|
| ![Gehäuse](../docs/case-assembly.png) | ![Explosionsansicht](../docs/case-exploded.png) |

## Dateien

| Datei | Inhalt |
|---|---|
| `stl/x3tuner-case-bottom.stl` | Unterschale: Akkufach, Auflagen für die Platine |
| `stl/x3tuner-case-lid.stl` | Deckel: Federtasten RESET/BOOT, LED-Fenster, Gravur |
| `stl/x3tuner-case-print.stl` | beide Teile druckfertig auf einer Platte (Deckel liegt kopfüber) |
| `x3tuner_case.scad` | parametrisches OpenSCAD-Modell |
| `board_data.scad` | Bauteilpositionen, automatisch aus `gen/circuit.py` erzeugt |

## Details

* **Akku:** Fach für einen **503040-LiPo** (30 × 40 × 5 mm, ca. 600 mAh) unter
  der Platine. Bis 34 × 43 mm Grundfläche passt alles. Für andere Akkus `BAT = [Breite, Länge, Dicke]` in
  der `.scad` ändern und neu exportieren.
* **USB-C** rechts, **Ein/Aus-Schieber** links mit Griffmulde. Den Hebel des
  MSK12C02 schiebst du mit dem Fingernagel.
* **SWD-Port** an der Stirnseite: Ein 5-poliges Dupont-Buchsengehäuse wird
  durch den Schlitz auf die Stiftleiste gesteckt. Die Pinbelegung (3V3, DIO, CLK, RST, GND) ist auf
  dem Deckel über jedem Pin eingraviert.
* **Tasten:** RESET und BOOT sind federnde Zungen im Deckel mit Stößel.
* **LEDs:** Über den LEDs bleiben nur 0,6 mm Material stehen. Bei **weißem oder
  hellgrauem** Filament leuchten Lade- und Status-LED durch, kleine Schächte
  verhindern, dass sich die Farben mischen. Bei dunklem Filament `SKIN = 0`
  setzen, dann entstehen offene Fenster.
* **Halt:** Der Deckel rastet mit vier Nasen ein. Vier Stifte im Deckel drücken die
  Platine auf ihre Auflagen, Schrauben braucht es nicht.

## Drucken

* PLA oder PETG, 0,2 mm Schichthöhe, 3 Wände, 15–20 % Infill, **ohne Stützen**.
* Unterschale mit dem Boden aufs Druckbett, **Deckel mit der Oberseite aufs Bett**.
  So liegt es schon in `print.stl`.
* Druckzeit ca. 1,5–2 h, ca. 15 g Material.

## Zusammenbau

1. Stiftleiste J3 an die Platine löten. Die kurzen Pin-Enden auf der Unterseite
   auf ca. 1 mm kürzen.
2. Akku mit doppelseitigem Klebeband ins Fach legen. Das Kabel zeigt zum
   SWD-Ende und wird dort nach oben zum Stecker J2 geführt.
3. Akku einstecken (**Polarität prüfen!**), Platine einlegen: USB-C links,
   Stiftleiste zum Schlitz.
4. Deckel aufsetzen und an allen vier Seiten einrasten lassen. Zum Öffnen an den
   Längsseiten leicht auseinanderziehen.

## Anpassen

```bash
# nach Änderungen an Platine (circuit.py) oder Gehäuse:
hardware/gen/make_case.sh     # board_data.scad, STL-Dateien, Bilder
```
Wichtige Parameter oben in `x3tuner_case.scad`: `BAT`, `WALL`, `FIT`
(Passung des Rastrands, bei strammem Sitz auf 0,2 erhöhen), `SKIN`, `TOP_CLEAR`.
