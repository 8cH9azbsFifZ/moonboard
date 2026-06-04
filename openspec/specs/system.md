# System Specification: Moonboard LED Controller

## Overview

A Raspberry Pi-based system that emulates the official Moonboard LED box, enabling the Moonboard smartphone app to control addressable LED strips via Bluetooth Low Energy (BLE). The system illuminates climbing holds on a home climbing wall to display boulder problems.

## Architecture

```
┌─────────────┐     BLE/UART      ┌──────────────────┐     MQTT/D-Bus     ┌────────────────┐
│ Moonboard   │ ───────────────── │ BLE Service      │ ──────────────────── │ LED Service    │
│ App (iOS)   │                   │ (raspi)          │                     │ (raspi)        │
└─────────────┘                   └──────────────────┘                     └────────────────┘
                                         │                                        │
                                    btmon sniffing                          SPI / WS2811
                                    + protocol decode                       via BiblioPixel
```

### Components

| Component | Location | Purpose |
|-----------|----------|---------|
| BLE Service | `ble/` | Emulates Moonboard LED box BLE GATT, sniffs btmon for incoming data |
| LED Service | `led/` | Drives WS2811/WS2801 LED strips via BiblioPixel library |
| Problem DB | `problems/` | Fetches, stores, and queries Moonboard problems from moonboard.com |
| Main Runner | `run.py` | D-Bus listener entry point (legacy, superseded by MQTT services) |

## BLE Service (`ble/`)

### Protocol

- **GATT Service UUID**: `6e400001-b5a3-f393-e0a9-e50e24dcca9e` (Nordic UART)
- **RX Characteristic**: `6e400002-b5a3-f393-e0a9-e50e24dcca9e` (write)
- **TX Characteristic**: `6e400003-b5a3-f393-e0a9-e50e24dcca9e`
- **Advertised Name**: `Moonboard A`

### Data Flow

1. App connects via BLE and sends problem data as UART writes
2. `btmon` subprocess captures raw HCI data packets
3. Hex data is extracted from lines containing `Data:`
4. `UnstuffSequence` reassembles fragmented BLE packets:
   - Start marker: `l#`
   - Stop marker: `#`
   - Flag packet: `~<flags>*` (e.g., `M` = Mini, `D` = BothLights)
5. Decoded problem string is parsed by `decode_problem_string()`
6. Result published via D-Bus signal (`com.moonboard` → `new_problem`) or MQTT (`moonboard/ble/problem`)

### Problem String Format

```
<type><position>,<type><position>,...
```

- Types: `S` (start), `E` (end/top), `P`/`R`/`L`/`M`/`F` (moves)
- Position: integer LED number, converted via `position_trans()` to grid coordinate (e.g., `A1`–`K18`)

### Grid Coordinate System

- Columns: `A`–`K` (11 columns, left to right)
- Rows: `1`–`18` (bottom to top, standard) or `1`–`12` (Mini board)
- Zigzag layout: odd columns count bottom→up, even columns top→down

### Implementations

| File | Backend | Status |
|------|---------|--------|
| `moonboard_ble_dbus_service.py` | D-Bus signal | Legacy |
| `moonboard_ble_service.py` | MQTT publish | **Current (v0.32+)** |

## LED Service (`led/`)

### Hardware Support

| Driver | Chip | Interface | Config |
|--------|------|-----------|--------|
| `PiWS281x` | WS2811 | GPIO (PWM) | Default for current setup |
| `WS2801` | WS2801 | SPI (`/dev/spidev0.1`) | Legacy |
| `SimPixel` | — | WebSocket (browser sim) | Development/testing |

### LED Mapping

LED position → grid coordinate mapping stored as JSON files:
- `led_mapping.json` — standard zigzag layout with LED_SPACING=3
- `led_mapping_3-Panels.json` — 3-panel variant
- `led_mapping_sequential.json` — sequential numbering

Key parameters:
- **Rows**: 18 (standard) or 12 (Mini)
- **Columns**: 11
- **Total holds**: 198 (standard)
- **LED_SPACING**: 3 (uses every 3rd LED on strip, for 10cm-spaced LEDs on 23cm hold spacing)
- **num_pixels**: defined in mapping JSON or calculated as `max(mapping.values()) + 1`

### Color Scheme

| Hold Type | Color |
|-----------|-------|
| START | Blue (0, 0, 255) |
| MOVES | Green (0, 255, 0) |
| TOP | Red (255, 0, 0) |

### Service Architecture

| File | Communication | Status |
|------|---------------|--------|
| `run.py` (root) | D-Bus listener | Legacy |
| `moonboard_led_service.py` | MQTT subscriber (`moonboard/ble/problem`) | **Current (v0.32+)** |

### LED Layouts (Hardcoded)

Two pre-defined panel layouts in `animation.py`:
- **nest**: 3-panel layout (top/middle/bottom, 6 rows each)
- **evo**: single zigzag column layout (18×11)

## Problem Database (`problems/`)

### Data Source

- Problems fetched from `https://www.moonboard.com/Problems/GetProblems` (POST, paginated)
- Requires authentication cookies (hardcoded, must be refreshed manually)
- Supports setups: `2016` (setupId=1), `master2017` (setupId=15)

### Database Schema (SQLite)

```sql
-- Tables: holds, problems, problemMoves, setter
-- holds(Position, Setup, HoldSet, Hold, Orientation)
-- problems(Id, Name, Grade, IsBenchmark, IsAssessmentProblem, Method, Firstname, Lastname)
-- problemMoves(Problem, Position, Setup, IsStart, IsEnd)
-- setter(Firstname, Lastname)
```

### Query Interface

- Async SQLite via `aiosqlite`
- `get_problem_holds(conn, Id)` → returns `{START: [], MOVES: [], TOP: []}`
- `user_query_get_problems(conn, Grades, Name, Setter, ...)` → filtered problem list
- Grade system: Font scale (`6A` to `8B+`)

## Hardware

### Raspberry Pi Configuration

- **Model**: Raspberry Pi Zero W
- **GPIO 26**: External power LED (output)
- **GPIO 3**: Power/clear button (input, pull-up, rising edge interrupt)
- **SPI**: LED strip data via `/dev/spidev0.1`

### Power Supply

- Meanwell MDR-60-5 (5V, 60W)
- Calculation: ~60mA × 200 LEDs = 12A → 60W

### LED Strips

- 4× 50 LED WS2811, 5V, 12mm
- Custom cable length: 23cm between LEDs (matching hold spacing)
- Alternative: 3× standard strips with 7cm spacing, using LED_SPACING=3

## Deployment

### Services (systemd)

| Service | Unit File | Description |
|---------|-----------|-------------|
| BLE | `moonboard_ble.service` | Bluetooth advertising + data capture |
| LED | `moonboard_led.service` | MQTT subscriber + LED driver |
| D-Bus (legacy) | `com.moonboard.service` | D-Bus service registration |

### Installation

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/8cH9azbsFifZ/moonboard/master/install/install.sh)"
```

Steps: prepare Raspi → install Python deps → install systemd services

### Dependencies

- Python 3 (Raspbian)
- BiblioPixel 3.4.46 (LED control)
- paho-mqtt (inter-service communication)
- dbus-python + GLib (legacy IPC)
- RPi.GPIO (button/LED)
- spidev + python-periphery (SPI for WS2801)
- rpi-ws281x 4.2.2 (PWM for WS2811)
- aiosqlite (async DB access)
- Pillow (problem visualization)

## Known Issues & Technical Debt

1. **Hardcoded cookies** in `fetch_problem.py` — expire, no refresh mechanism
2. **Dual backends** — D-Bus (legacy) and MQTT (current) coexist, dead code remains
3. **FIXMEs in code** — ~20+ scattered across codebase (paths, configs, dead code)
4. **No config file** — setup, brightness, MQTT host are hardcoded or CLI args only
5. **`btmon` sniffing** — fragile, depends on parsing terminal output with ANSI codes
6. **No error recovery** — BLE reconnection issues documented but not solved
7. **Missing `errno` import** in `OutStream` class (both BLE service files)
8. **SQL injection risk** in `user_query_get_problems()` — string formatting for queries
9. **No tests** — zero test coverage
10. **Inconsistent LED mapping** — `moonboard.py` and `animation.py` define different `MoonBoard` classes

## Tested Configurations

- Raspberry Pi Zero W
- iPhone 5, 8, X, 11 (iOS ≥ 14)
- Moonboard App (standard)
- Hold setups: 2016, MoonboardMasters2017
