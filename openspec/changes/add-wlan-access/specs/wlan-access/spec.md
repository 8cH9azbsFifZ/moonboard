## ADDED Requirements

### Requirement: Show a problem over HTTPS
The Pi SHALL accept `POST /problem` with a JSON body containing `START`, `MOVES` and `TOP` (optional `LEFT`, `FOOT`, `MATCH`) and SHALL publish it unchanged to the MQTT topic `moonboard/ble/problem`.

#### Scenario: Valid problem
- **WHEN** `{"START":["A1"],"MOVES":["F9"],"TOP":["K18"]}` is posted
- **THEN** the response is 200 with `"ok": true` and the wall lights A1, F9 and K18

#### Scenario: Invalid position
- **WHEN** a problem contains `"L5"` or `"A19"`
- **THEN** the response is 400 naming the invalid position and nothing is published

### Requirement: Clear the wall
The Pi SHALL accept `POST /clear` and switch off all LEDs.

#### Scenario: Clear
- **WHEN** `/clear` is posted
- **THEN** no LED is lit

### Requirement: Status
The Pi SHALL answer `GET /status` with the service version, whether MQTT is connected, and the last problem shown with its time.

#### Scenario: Status after a problem
- **WHEN** a problem was shown and `/status` is requested
- **THEN** the response contains that problem and `"mqtt": true`

### Requirement: Trusted TLS and CORS
The service MUST use a certificate the household devices already trust and SHALL allow cross-origin requests only from the configured app origins.

#### Scenario: App origin
- **WHEN** a request carries `Origin: https://10.101.2.71:8443`
- **THEN** the response echoes it in `Access-Control-Allow-Origin`

#### Scenario: Foreign origin
- **WHEN** a request carries `Origin: https://example.com`
- **THEN** the response has no `Access-Control-Allow-Origin` header
