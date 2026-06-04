## 1. Code Cleanup & Dead Code Removal

- [ ] 1.1 Remove the legacy D-Bus BLE service (`ble/moonboard_ble_dbus_service.py`) or clearly mark as deprecated with README note
- [ ] 1.2 Remove duplicate `MoonBoard` class in `led/animation.py` — consolidate into `led/moonboard.py`
- [ ] 1.3 Add missing `import errno` in `OutStream` class in `ble/moonboard_ble_service.py`
- [ ] 1.4 Remove commented-out code and resolve FIXMEs (prioritize: hardcoded paths, config values)
- [ ] 1.5 Remove legacy `run.py` D-Bus entry point or document it as deprecated in favor of MQTT services

## 2. Configuration Externalization

- [ ] 2.1 Create a `config.yaml` or `.env` file for: MQTT broker host/port, LED driver type, LED mapping file, brightness, board setup
- [ ] 2.2 Update `moonboard_ble_service.py` to read MQTT broker config from config file
- [ ] 2.3 Update `moonboard_led_service.py` to read driver/mapping/brightness from config file
- [ ] 2.4 Document all configuration options in README

## 3. Bug Fixes

- [ ] 3.1 Fix `errno` NameError in `OutStream.read_lines()` — add `import errno` at top of both BLE service files
- [ ] 3.2 Fix SQL injection in `problems/db_query.py` `user_query_get_problems()` — use parameterized queries for Name and Setter
- [ ] 3.3 Fix relative path issue in `moonboard.py` `display_holdset()` (`'../problems/HoldSetup.json'`) — use `pathlib` with `__file__` reference

## 4. Testing

- [ ] 4.1 Add unit tests for `moonboard_app_protocol.py`: `UnstuffSequence` and `decode_problem_string` with known input/output pairs
- [ ] 4.2 Add unit tests for LED mapping: verify all 198 grid coordinates (A1–K18) map to valid LED indices
- [ ] 4.3 Add integration test for MQTT message flow: publish problem JSON → verify LED service calls `show_problem` correctly
- [ ] 4.4 Add test for `position_trans()` function with both 18-row and 12-row grids

## 5. Documentation

- [ ] 5.1 Update `doc/OVERVIEW-SOFTWARE.md` to reflect MQTT architecture (currently describes D-Bus)
- [ ] 5.2 Document MQTT topic contract: topic names, message format, QoS expectations
- [ ] 5.3 Add troubleshooting section for common btmon/BLE issues
- [ ] 5.4 Archive the system spec from `openspec/specs/system.md` into project documentation

## 6. Reconnection & Reliability

- [ ] 6.1 Add BLE advertising watchdog: restart advertising if no connection received within timeout
- [ ] 6.2 Add MQTT reconnect logic with exponential backoff in LED service
- [ ] 6.3 Add logging for packet decode errors (currently silently discarded)
- [ ] 6.4 Add systemd `Restart=on-failure` to service unit files if not already present
