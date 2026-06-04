## ADDED Requirements

### Requirement: BLE advertising as Moonboard LED box
The system SHALL advertise via BLE using the Nordic UART Service UUID `6e400001-b5a3-f393-e0a9-e50e24dcca9e` with the local name `Moonboard A`, making it discoverable by the official Moonboard smartphone app.

#### Scenario: App discovers the device
- **WHEN** the Moonboard app scans for BLE devices
- **THEN** the system appears as "Moonboard A" with the correct UART service UUID

#### Scenario: Advertising restarts after problem received
- **WHEN** a complete problem has been decoded and published
- **THEN** the system SHALL restart BLE advertising to accept new connections

### Requirement: BLE data capture via btmon
The system SHALL capture incoming BLE write data by monitoring `btmon` output, extracting hex-encoded payloads from lines containing the string `Data:`.

#### Scenario: Raw BLE data extraction
- **WHEN** btmon outputs a line containing `Data:` followed by hex bytes
- **THEN** the system SHALL strip whitespace, ANSI escape codes (`\x1b`, `[0m`), and the `Data:` prefix, yielding a clean hex string

#### Scenario: Non-data lines are ignored
- **WHEN** btmon outputs a line without `Data:`
- **THEN** the system SHALL not process that line

### Requirement: Packet unstuffing for fragmented BLE data
The system SHALL reassemble fragmented BLE packets using start marker `l#` and stop marker `#`. Intermediate fragments without markers SHALL be concatenated in order.

#### Scenario: Single-packet problem (fits in one BLE write)
- **WHEN** a data packet starts with `l#` and ends with `#`
- **THEN** the system SHALL return the content between markers as a complete problem string

#### Scenario: Multi-packet problem (fragmented)
- **WHEN** a data packet starts with `l#` but does not end with `#`
- **THEN** the system SHALL buffer the content and wait for subsequent packets until one ending with `#` arrives, then return the concatenation

#### Scenario: Flag packet processing
- **WHEN** a data packet starts with `~` and ends with `*`
- **THEN** the system SHALL extract the flags between those markers (e.g., `M` for Mini board, `D` for dual lights) and store them for the next problem

#### Scenario: Error recovery on unexpected start
- **WHEN** a start marker `l#` is received while already buffering a previous incomplete sequence
- **THEN** the system SHALL discard the previous buffer and start fresh

### Requirement: Problem string decoding
The system SHALL decode a problem string of format `<type><position>,<type><position>,...` into a structured hold map with keys START, MOVES, and TOP.

#### Scenario: Standard board decoding (18 rows)
- **WHEN** the flags do NOT contain `M` and a problem string is decoded
- **THEN** positions SHALL be converted using 18-row grid: column = position // 18, row = (position % 18) + 1, with odd columns reversed (row = 19 - row)

#### Scenario: Mini board decoding (12 rows)
- **WHEN** the flags contain `M`
- **THEN** positions SHALL be converted using 12-row grid: column = position // 12, row = (position % 12) + 1, with odd columns reversed (row = 13 - row)

#### Scenario: Hold type classification
- **WHEN** a hold entry has type `S`
- **THEN** it SHALL be classified as START
- **WHEN** a hold entry has type `E`
- **THEN** it SHALL be classified as TOP
- **WHEN** a hold entry has type `P`, `R`, `L`, `M`, or `F`
- **THEN** it SHALL be classified as MOVES

### Requirement: Problem publication via MQTT
The system SHALL publish decoded problems as JSON to MQTT topic `moonboard/ble/problem` on the configured broker.

#### Scenario: Successful problem publication
- **WHEN** a problem is fully decoded (unstuffed + parsed)
- **THEN** the system SHALL publish a JSON object `{"START": [...], "MOVES": [...], "TOP": [...]}` to `moonboard/ble/problem`

#### Scenario: MQTT connection at startup
- **WHEN** the BLE service starts
- **THEN** it SHALL connect to the MQTT broker and publish status `Starting` to `moonboard/ble/status`
