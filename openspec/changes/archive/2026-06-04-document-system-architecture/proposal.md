## Why

This project lacks formal documentation of its system architecture, component interactions, and behavioral requirements. The codebase has evolved organically (v0.23→v0.32) with dual backends (D-Bus legacy + MQTT current), ~20 FIXMEs, zero tests, and no specification. A clear spec is needed to enable safe refactoring, onboarding, and future development (e.g., removing dead code, adding tests, fixing reconnection issues).

## What Changes

- Document the complete system architecture: BLE service, LED service, problem database
- Specify the Moonboard app BLE protocol (packet unstuffing, problem string format, grid coordinate system)
- Define LED mapping and hardware configuration requirements
- Capture the MQTT-based inter-service communication contract
- Identify and document known technical debt and open issues

## Capabilities

### New Capabilities
- `ble-protocol`: BLE advertising, GATT service, btmon sniffing, packet unstuffing, and problem string decoding
- `led-control`: LED strip driving via BiblioPixel, mapping grid coordinates to physical LEDs, color schemes, animations
- `problem-database`: Fetching, storing, and querying Moonboard problems from SQLite
- `system-integration`: Inter-service communication (MQTT topics, D-Bus signals), systemd deployment, hardware GPIO

### Modified Capabilities
<!-- No existing specs to modify — this is the initial specification -->

## Impact

- All source files in `ble/`, `led/`, `problems/`, and `run.py`
- Systemd service definitions (`moonboard_ble.service`, `moonboard_led.service`, `com.moonboard.service`)
- Hardware configuration (GPIO 3/26, SPI, BLE adapter hci0)
- MQTT broker dependency (`raspi-moonboard:1883`)
- External dependency on moonboard.com API (problem fetching)
