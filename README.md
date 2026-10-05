# x3utils-esp32

A **standalone ESP32 flasher for the AT32F415 VCU** on X3-family e-scooters
(ZT3 Pro, Max G3, F3 / F3 Pro), controlled entirely from your **phone's browser
over WiFi**.

No PC. No ST-LINK. No app install. The ESP32 *is* the programmer: it bit-bangs
SWD to the scooter's debug pins itself, and hosts a web UI you drive from
Safari on an iPhone (or any browser — WiFi, so the Chrome/WebUSB limitation of
the original web app does not apply).

This is an ESP32 port of [**x3utils**](https://github.com/ztakis/x3utils). The
flashing *brains* — the AT32F415 erase/program/verify sequence, the FAP
read-protection check and rescue, the SHU-compatibility patch and its firmware
safety gates — are ported straight from the upstream engine. Only the transport
changed: an ESP32 GPIO SWD master replaces the ST-LINK, and a built-in web
server replaces the desktop GUI.

> [!WARNING]
> This tool writes the scooter VCU directly. A wrong file, a bad contact, or an
> interrupted flash can leave the controller unusable until recovered. **Always
> make a full backup first and keep it safe.** Use 3.3 V logic only, and power
> the VCU from **one** source at a time.

> [!IMPORTANT]
> **On-hardware validation status.** The firmware-identity / SHU-compat safety
> gates and the Thumb-2 version decoder are covered by host unit tests (see
> `host_test/`). The bit-banged SWD transaction layer (`swd.cpp`) follows the
> standard ADIv5 framing but has **not** been bench-verified against a real
> AT32F415 in this repository's CI (none exists). Treat your first connection as
> a bring-up: start with **Check connection** and **Backup**, confirm a clean
> 128 KB read, and only then flash. If you see `no ACK` / parity errors, raise
> the **SWD half-clock µs** setting (1–3) for a slower, more tolerant line.

---

## What it does

Same operations as the desktop/web app, from the browser:

- **Check connection** — read-only probe + target identification.
- **Backup 128 KB** — full dump, validated, downloaded to your phone as a `.bin`.
- **Backup + Flash** — upload a full 128 KB `.bin`; it erases, writes, verifies.
- **Flash slot 0** — upload a slot-0 `.bin` (identity-preserving).
- **Check protection** — read-only FAP (read-protection) verdict.
- **Unlock / Rescue** — clears FAP; this **mass-erases** main flash (recovery path).
- **Make SHU compatible** — dumps, patches the chip's own firmware at `0x1420`,
  and flashes it back. Safety-gated exactly like upstream: refuses non-factory
  firmware, XTEA-present (too-new) firmware, unsupported models (GT3), and
  blacklisted/unidentified versions.

Connection modes: **Default SWD**, **Under-reset (nRST)**, and **Power-race**
(hammer connect while you apply power).

---

## Hardware

- An **ESP32** board (classic ESP32, or an S3 / C3 — see `platformio.ini`).
- Four wires to the scooter's debug header: **SWCLK**, **SWDIO**, **GND**, and
  **nRST / C45** (strongly recommended — needed for Under-reset mode and most
  reliable for locked/running targets).
- A 3.3 V power path for the VCU (bench/main power **or** the ESP32 3V3 pin —
  never both). See the upstream wiki's per-model guides for pad locations and
  the C45 point.

### Default pin map (classic ESP32 — change in `src/config.h` or the UI)

| Signal | GPIO |
|--------|------|
| SWCLK  | 18   |
| SWDIO  | 19   |
| nRST   | 21   |
| GND    | any GND |

S3/C3 defaults are different — see `src/config.h`.

---

## Build & flash the ESP32

Uses [PlatformIO](https://platformio.org/).

```bash
# classic ESP32
pio run -e esp32dev -t upload

# or an S3 / C3 board
pio run -e esp32-s3 -t upload
pio run -e esp32-c3 -t upload

# watch the serial log (shows the WiFi IP)
pio device monitor -b 115200
```

First boot creates a **WiFi hotspot**:

- SSID: `x3utils-esp32`  ·  password: `x3utils123`
- Join it from your phone, then open **http://192.168.4.1/** (or
  **http://x3utils.local/**).

To join your own network instead, open **Settings → WiFi → Join network** in the
UI, enter your SSID/password, and save (the ESP32 reboots and connects; find its
IP on the serial monitor or your router).

---

## Using it from your phone

1. Wire SWCLK / SWDIO / GND / nRST to the VCU, power the VCU from one source.
2. Join the ESP32 hotspot and open the page.
3. Pick a connection mode (start with **Default SWD**; use **Under-reset** if the
   firmware keeps SWD disabled while running).
4. **Check connection** → you should see the AT32F415 part identified.
5. **Backup 128 KB** → wait for "Backup complete", then **Download last backup**.
6. Only now flash: **Backup + Flash** / **Flash slot 0** (upload a `.bin`), or
   **Make SHU compatible**.

The console streams live log + progress over a WebSocket. **Abort** stops a
running operation (safe between steps; a flash in progress finishes its current
word).

---

## How the port works

The upstream engine is written against a tiny debug-probe surface — read/write a
debug register, read/write memory, drive nRST. `src/swd.cpp` provides exactly
that surface by bit-banging ADIv5 SWD on two GPIOs, so the AT32 flash algorithm
in `src/at32.cpp` is the *same* algorithm the desktop/web app runs:

```
browser ──HTTP/WebSocket──> ESP32 web server (main.cpp)
                                  │  queues one command
                                  ▼
                            x3_ops.cpp  (Check/Backup/Flash/Compat/Protection)
                                  │
                      at32.cpp (Cortex-M + AT32F415 flash)   fw_ident.cpp (SHU gates)
                                  │
                              swd.cpp  (bit-banged ADIv5 SWD)
                                  │  SWCLK / SWDIO / nRST
                                  ▼
                           AT32F415 VCU
```

The experimental SRAM flash loader from upstream is intentionally **not** ported;
this uses the field-proven direct word-write path. The SHU-compat patch,
factory-state check, XTEA gate, model allow-list, and the Thumb-2 version
blacklist/known-version decoder are ported faithfully in `src/fw_ident.cpp`.

### Source layout

```
src/
  config.h       pins, WiFi defaults, SWD timing, target geometry
  swd.{h,cpp}    bit-banged ADIv5 SWD master (the ST-LINK replacement)
  at32.{h,cpp}   Cortex-M debug + AT32F415 detect / erase / program / verify / FAP
  fw_ident.{h,cpp}  banner, factory-state, version matrix, SHU-compat gates
  x3_ops.{h,cpp} high-level operations driven by the UI
  web_ui.h       the mobile web UI (served from flash)
  main.cpp       WiFi + web server + WebSocket + routing + settings
host_test/            host unit tests for the safety gates (see below)
```

## Tests

The portable safety-critical logic has host-side unit tests (no hardware, no
ESP toolchain needed):

```bash
cd host_test
g++ -std=gnu++17 -I shim -I ../src test_fwident.cpp ../src/fw_ident.cpp -o t && ./t
```

They cover the Thumb-2 version decoder, the blacklist floor, the XTEA / factory
/ already-compatible / unidentified refusals, the MCU model requirement, and the
16-byte compat patch.

---

## Credits & license

MIT. Ported from [x3utils](https://github.com/ztakis/x3utils) (© ztakis) and its
swdart engine (© nopbxlr). See [LICENSE](LICENSE). Supported models and the
firmware version matrix mirror upstream; consult the upstream wiki for wiring,
C45 locations, and SHU-compat firmware limits.
