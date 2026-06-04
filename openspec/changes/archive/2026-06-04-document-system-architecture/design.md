## Context

The Moonboard LED Controller is a Raspberry Pi Zero W-based system that emulates the official Moonboard LED box hardware. It intercepts BLE communication from the Moonboard smartphone app, decodes the proprietary problem transmission protocol, and drives addressable WS2811 LED strips to illuminate climbing holds.

The system has evolved through several iterations (v0.23–v0.32), transitioning from a D-Bus-based monolithic architecture to a decoupled MQTT-based microservice design with two independent systemd services.

Current architecture:
```
[Moonboard App] --BLE UART--> [btmon] --stdout--> [BLE Service] --MQTT--> [LED Service] --SPI/GPIO--> [WS2811 LEDs]
```

## Goals / Non-Goals

**Goals:**
- Document the existing system behavior as-is for future maintainability
- Define clear interfaces between BLE and LED services (MQTT contract)
- Capture the proprietary protocol reverse-engineering (packet unstuffing, position encoding)
- Enable future refactoring by establishing testable specifications

**Non-Goals:**
- Redesigning the architecture (this change documents, not modifies)
- Replacing the btmon-sniffing approach (known fragility, but works)
- Adding authentication or security hardening
- Supporting additional board types beyond Standard (18-row) and Mini (12-row)

## Decisions

### D1: MQTT over D-Bus for inter-service communication
**Decision**: Use MQTT (paho-mqtt) as the primary IPC mechanism.
**Rationale**: D-Bus requires complex boilerplate (bus names, interfaces, signals) and tight coupling. MQTT is fire-and-forget, supports multiple subscribers, and is debuggable with standard tools (`mosquitto_sub`). The MQTT broker also enables future extensions (web dashboard, logging service).

### D2: btmon sniffing over GATT WriteValue callback
**Decision**: Capture BLE data by parsing `sudo btmon` stdout rather than relying on the BlueZ GATT WriteValue callback.
**Rationale**: The GATT WriteValue callback proved unreliable across iOS versions. btmon captures raw HCI data regardless of the higher-level BlueZ stack state. Trade-off: requires sudo, fragile string parsing, ANSI code stripping.

### D3: BiblioPixel as LED abstraction layer
**Decision**: Use BiblioPixel 3.4.x for LED strip control.
**Rationale**: Provides a unified API across multiple LED chip types (WS2811/WS2801), supports threaded updates, and includes a SimPixel browser simulator for development without hardware.

### D4: JSON-based LED mapping
**Decision**: Store LED position mappings as JSON files rather than computed at runtime.
**Rationale**: Different physical installations have different wiring patterns (zigzag, sequential, 3-panel). A JSON file per layout allows configuration without code changes. The `create_nth_led_layout.py` script generates these mappings for custom installations.

### D5: Stateless BLE protocol handling
**Decision**: The UnstuffSequence class maintains minimal state (current buffer + flags) and resets on each complete problem.
**Rationale**: BLE connections are unreliable. Minimal state means quick recovery from corrupted/partial transmissions. Error cases (unexpected start markers) simply reset the buffer.

## Risks / Trade-offs

### R1: btmon dependency is fragile
btmon output format may change across BlueZ versions. ANSI escape codes in output require stripping. The system runs btmon as a subprocess with sudo, creating a privilege escalation surface.

### R2: No reconnection handling
When BLE connection drops mid-transmission, the partial buffer is eventually discarded (on next start marker), but there's no active detection or notification. The user must re-send the problem from the app.

### R3: Hardcoded MQTT broker hostname
The broker address `raspi-moonboard:1883` is hardcoded in both services. Moving to a different host requires code changes.

### R4: Missing errno import
Both `moonboard_ble_dbus_service.py` and `moonboard_ble_service.py` reference `errno.EIO` in OutStream without importing `errno`. This would cause a NameError on pipe read failure.

### R5: SQL injection in query interface
`user_query_get_problems()` uses f-string formatting for Name and Setter parameters directly in SQL, enabling injection attacks. Acceptable for local use but a risk if exposed via API.

### R6: Dual MoonBoard classes
`led/moonboard.py` and `led/animation.py` both define a `MoonBoard` class with different implementations. The `run.py` imports from `led.moonboard` while `animation.py`'s LED_LAYOUT dict is used in `run.py`. This creates confusion about which class handles what.
