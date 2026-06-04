## ADDED Requirements

### Requirement: MQTT-based inter-service communication
The BLE service and LED service SHALL communicate via MQTT broker. The BLE service publishes decoded problems; the LED service subscribes and displays them.

#### Scenario: BLE publishes problem
- **WHEN** the BLE service decodes a complete problem
- **THEN** it SHALL publish the JSON-encoded problem to topic `moonboard/ble/problem` on broker `raspi-moonboard:1883`

#### Scenario: LED subscribes to problems
- **WHEN** the LED service starts
- **THEN** it SHALL connect to the MQTT broker and subscribe to `moonboard/ble/problem`

#### Scenario: End-to-end problem flow
- **WHEN** the Moonboard app sends a problem via BLE
- **THEN** the BLE service SHALL decode it, publish to MQTT, the LED service SHALL receive it, and the LEDs SHALL illuminate the correct holds within the update interval (1.0 seconds)

### Requirement: Systemd service deployment
Each component SHALL run as a systemd service with automatic startup on boot.

#### Scenario: BLE service startup
- **WHEN** the system boots
- **THEN** `moonboard_ble.service` SHALL start automatically, begin BLE advertising, and monitor btmon

#### Scenario: LED service startup
- **WHEN** the system boots
- **THEN** `moonboard_led.service` SHALL start automatically, connect to MQTT, and wait for problems

#### Scenario: Service restart on failure
- **WHEN** a service is stopped via `systemctl stop`
- **THEN** it SHALL cleanly shut down (stop advertising, disconnect MQTT, turn off LEDs)

### Requirement: GPIO hardware control
The system SHALL control external power LED and clear button via GPIO.

#### Scenario: Power LED indication
- **WHEN** the main service starts
- **THEN** GPIO 26 SHALL be set HIGH to illuminate the external power LED

#### Scenario: Button press clears display
- **WHEN** the button on GPIO 3 is pressed (rising edge with 300ms debounce)
- **THEN** the system SHALL call `clear()` to turn off all LEDs

### Requirement: Installation automation
The system SHALL provide an automated installation script that configures a fresh Raspbian system.

#### Scenario: Fresh install from curl
- **WHEN** the install script is executed on a fresh Raspbian Buster system
- **THEN** it SHALL prepare the Raspi (enable SPI, BLE), install Python dependencies from `requirements.txt`, and install/enable all systemd services

#### Scenario: Python dependencies
- **WHEN** `20-prepare-python.sh` runs
- **THEN** all packages from `install/requirements.txt` SHALL be installed (BiblioPixel, paho-mqtt, rpi-ws281x, spidev, etc.)

### Requirement: D-Bus legacy backend (deprecated)
The system SHALL maintain backward compatibility with the D-Bus-based communication for the `run.py` entry point, though MQTT is the preferred backend.

#### Scenario: D-Bus signal emission
- **WHEN** the D-Bus BLE service decodes a problem
- **THEN** it SHALL emit signal `new_problem` on interface `com.moonboard` with the JSON-encoded problem string

#### Scenario: D-Bus signal reception in run.py
- **WHEN** `run.py` is running and a `new_problem` signal is received on D-Bus
- **THEN** it SHALL parse the JSON holds and call `show_problem()` on the MoonBoard LED controller
