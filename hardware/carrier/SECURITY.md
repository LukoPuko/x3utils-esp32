# Firmware schützen: nicht auslesbar, nicht fremd-flashbar, nur OTA-Update

Ziel: Die fertige Firmware auf dem ESP32-C3 soll **nicht ausgelesen** und **nicht
über USB neu geflasht** werden können. Updates kommen nur noch **per WLAN über
die App** (signiert). Das sind drei eFuse-Schutzmechanismen plus OTA:

| Schutz | Was er bewirkt |
|---|---|
| **Flash-Verschlüsselung** (AES-128 XTS) | Der Flash ist verschlüsselt. Wer ihn ausliest, bekommt nur Chiffrat. Der Schlüssel liegt in einem eFuse, der nicht auslesbar ist. |
| **Secure Boot v2** (RSA-3072) | Der Bootloader startet nur Firmware, die mit **deinem** privaten Schlüssel signiert ist. Fremde oder manipulierte Images booten nicht – das gilt auch für OTA-Images. |
| **Download-Modus sperren** | Der ROM-/USB-Serial-JTAG-Download wird per eFuse abgeschaltet. Dann kann niemand mehr über USB lesen oder schreiben, auch nicht mit `esptool`. |
| **OTA** (`src/ota.h`, `POST /api/ota`) | Der einzige verbleibende Update-Weg: Die App schickt die signierte Firmware per WLAN. |

> [!WARNING]
> **eFuses sind einmalig und unwiderruflich.** Einmal gebrannt, lässt sich das
> nicht rückgängig machen. Teste den ganzen Ablauf zuerst an einem
> **Opfer-Modul**. Verlierst du den Secure-Boot-Schlüssel, kannst du dem Gerät
> **nie wieder** ein Update geben. Ist der Download-Modus gesperrt und ein OTA
> schlägt fehl, ist das Modul nur noch über OTA erreichbar – ein Fehler im
> OTA-Pfad macht es unbrauchbar. Darum: erst testen, dann in Serie.

> [!NOTE]
> Diese Schritte laufen mit **Espressifs ESP-IDF-Werkzeugen** (`idf.py`,
> `esptool.py`, `espefuse.py`, `espsecure.py`), nicht allein mit Arduino/
> PlatformIO. Der Arduino-Build liefert nur die Anwendung; Secure Boot und
> Flash-Verschlüsselung richtet man mit der IDF ein (Arduino kann als
> IDF-Komponente eingebunden werden). Ich konnte das hier nicht flashen oder
> testen – prüfe jeden Schritt an Espressifs Doku für den **ESP32-C3**.

## 1. Vorbereiten: Schlüssel erzeugen und sicher aufbewahren

```bash
# Secure-Boot-Signierschlüssel (RSA-3072). GEHEIM halten, mehrfach sichern!
espsecure.py generate_signing_key --version 2 secure_boot_signing_key.pem
```

Dieser Schlüssel signiert die Firmware – jetzt und für jedes spätere OTA-Update.
Ohne ihn kein Update mehr. Bewahre ihn offline auf (z. B. Passwort-Manager +
Offline-Backup), nicht im Git-Repo.

## 2. In der ESP-IDF aktivieren (`idf.py menuconfig`)

- **Security features → Enable flash encryption on boot**
  - Modus: für die Serie **Release** (Development erlaubt Umflashen und schützt
    nicht wirklich).
- **Security features → Enable hardware Secure Boot in bootloader (v2)**
  - Signierschlüssel: `secure_boot_signing_key.pem` aus Schritt 1.
- **Security features → Potentially insecure options**
  - **Deaktiviert** lassen: „Allow potentially insecure options".
- Der Release-Modus brennt beim ersten Boot automatisch die passenden eFuses
  und schaltet den unsicheren Download-Modus ab.

## 3. Bauen und zum ersten Mal flashen

```bash
idf.py build
idf.py flash               # bootloader, partition table, signierte App
idf.py monitor             # erster Boot verschlüsselt den Flash (dauert etwas)
```

Nach dem ersten Boot ist der Flash verschlüsselt und Secure Boot aktiv.

## 4. Download-Modus endgültig sperren

Flash-Verschlüsselung (Release) + Secure Boot sperren den normalen Download
schon. Wer **jeglichen** USB-Zugriff ausschließen will, brennt zusätzlich (C3):

```bash
# Erst prüfen, was gesetzt ist:
espefuse.py summary

# ROM-Download komplett aus (danach KEIN esptool-Zugriff mehr):
espefuse.py burn_efuse DIS_DOWNLOAD_MODE
# USB-Serial-JTAG aus (der C3 flasht/liest sonst über seinen nativen USB):
espefuse.py burn_efuse DIS_USB_SERIAL_JTAG
# JTAG dauerhaft aus:
espefuse.py burn_efuse DIS_PAD_JTAG DIS_USB_JTAG
```

Alternativ statt komplett sperren: **Secure Download Mode**
(`ENABLE_SECURITY_DOWNLOAD`) erlaubt nur noch verschlüsseltes Schreiben
bestimmter Bereiche, kein Auslesen. Für „gar kein USB" ist `DIS_DOWNLOAD_MODE`
der stärkere Schutz.

> Danach ist das Gerät über USB tot für Flasher. Ab hier geht nur noch OTA.

## 5. OTA-Updates signieren und ausliefern

Jedes neue Firmware-Image muss mit demselben Schlüssel signiert sein, sonst
weist Secure Boot es beim Reboot ab:

```bash
idf.py build                         # IDF signiert das App-Image automatisch
# oder ein fertiges Image nachträglich signieren:
espsecure.py sign_data --version 2 --keyfile secure_boot_signing_key.pem \
    --output x3carrier-signed.bin  build/x3utils-esp32.bin
```

Die App lädt `x3carrier-signed.bin` hoch:

```
POST http://<geraet>/api/ota
Header:  X-OTA-Token: <WLAN-AP-Passwort des Geräts>
Body:    die rohe, signierte .bin
```

Der ESP32 schreibt das Image in den zweiten App-Slot (Partition `min_spiffs`,
siehe `platformio.ini`) und startet neu. Der Bootloader prüft die Signatur; ist
sie falsch, bootet das alte Image weiter. Der Token (per Default das
AP-Passwort) verhindert nur, dass Fremde im WLAN ein Update anstoßen – die
Echtheit garantiert Secure Boot.

### Ohne vollen Secure-Boot-Aufwand

Reicht dir „nur per App updatebar, nicht versehentlich überschreibbar" und du
willst die eFuse-Prozedur (noch) nicht brennen, dann nutzt du nur den
OTA-Endpunkt (`-DX3_OTA`, schon im `x3carrier`-Build). Dann ist die Firmware
zwar weiter über USB auslesbar, aber Updates laufen sauber über die App. Den
echten Auslese- und Flash-Schutz bringen erst die eFuses oben.

## Was ist schon im Build

- `src/ota.h` + `-DX3_OTA` und die OTA-Partition `min_spiffs.csv` sind im
  `[env:x3carrier]` aktiv (`platformio.ini`).
- Flash-Verschlüsselung, Secure Boot und das Sperren des Download-Modus sind
  **bewusst nicht** automatisiert – sie sind unwiderruflich und gehören in einen
  kontrollierten Produktionsschritt mit gesichertem Schlüssel.

Espressif-Doku (ESP32-C3): „Flash Encryption", „Secure Boot V2" und „eFuse
Manager" im ESP-IDF Programming Guide.
