## ADDED Requirements

### Requirement: LED strip initialization with driver selection
The system SHALL support multiple LED drivers (PiWS281x, WS2801, SimPixel) and initialize the strip with the configured number of pixels and brightness level.

#### Scenario: PiWS281x driver initialization
- **WHEN** driver_type is `PiWS281x`
- **THEN** the system SHALL initialize a PiWS281X driver with GPIO-based PWM control

#### Scenario: WS2801 driver initialization
- **WHEN** driver_type is `WS2801`
- **THEN** the system SHALL initialize a WS2801 SPI driver on `/dev/spidev0.1` with periphery interface at speed 1

#### Scenario: SimPixel driver for development
- **WHEN** driver_type is `SimPixel`
- **THEN** the system SHALL initialize a SimPixel WebSocket driver and open a browser for visual simulation

#### Scenario: Fallback to dummy driver
- **WHEN** the configured driver fails to initialize (ImportError or ValueError)
- **THEN** the system SHALL fall back to DriverDummy and log the error

### Requirement: Grid coordinate to LED index mapping
The system SHALL map grid coordinates (A1–K18) to physical LED indices using a JSON mapping file. The mapping accounts for zigzag wiring patterns and LED spacing.

#### Scenario: Standard mapping lookup
- **WHEN** a hold coordinate like `E10` is requested
- **THEN** the system SHALL return the corresponding LED index from the loaded JSON mapping

#### Scenario: LED spacing for non-standard strips
- **WHEN** LED strips with 10cm spacing are used on a 23cm hold grid
- **THEN** every 3rd LED SHALL be used (LED_SPACING=3), with intermediate LEDs unused

#### Scenario: Custom mapping via JSON file
- **WHEN** a custom `led_mapping.json` is provided
- **THEN** the system SHALL load and use that mapping, determining num_pixels from either the `num_pixels` key or `max(values) + 1`

### Requirement: Problem display with color-coded holds
The system SHALL display a problem by lighting holds in three colors: START (blue), MOVES (green), TOP (red). All other LEDs SHALL be off.

#### Scenario: Display a complete problem
- **WHEN** `show_problem` is called with holds `{"START": ["A1"], "MOVES": ["C5","D8"], "TOP": ["K18"]}`
- **THEN** A1 SHALL light blue, C5 and D8 SHALL light green, K18 SHALL light red, all other LEDs SHALL be off

#### Scenario: Clear display
- **WHEN** `clear` is called
- **THEN** all LEDs SHALL turn off and any running animation SHALL stop

### Requirement: LED layout test sequence
The system SHALL provide a test mode that sequentially illuminates each hold position (A1→K18) in alternating red/blue to verify wiring correctness.

#### Scenario: Full grid test
- **WHEN** `led_layout_test` is called with a duration
- **THEN** the system SHALL iterate through all 198 hold positions (11 columns × 18 rows), briefly lighting each in red then blue

### Requirement: Hold set display
The system SHALL display all holds belonging to a specific hold set (A, B, C, Original School Holds, Wooden Holds) in green for the configured setup.

#### Scenario: Display Hold Set A
- **WHEN** `display_holdset("Hold Set A")` is called
- **THEN** all holds from Hold Set A in the current setup SHALL light green, remaining holds SHALL be off, and the display SHALL persist for the configured duration before clearing

### Requirement: MQTT-based problem reception
The LED service SHALL subscribe to MQTT topic `moonboard/ble/problem` and display received problems on the LED strip.

#### Scenario: Problem received via MQTT
- **WHEN** a JSON message with START, MOVES, and TOP arrays is received on `moonboard/ble/problem`
- **THEN** the system SHALL clear the current display and light the holds with the standard color scheme (START=green/0,255,0, MOVES=blue/0,0,255, TOP=red/255,0,0)
