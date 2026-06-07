## Why

The Moonboard iOS app scans for a BLE device named **"Moonboard A"**. The Raspberry Pi
broadcasts its system hostname (e.g. `raspi-moonboard`) as the BLE adapter name. Even
when the BLE peripheral service correctly registered a `LocalName: Moonboard A` in
the GATT advertisement scan response, the *adapter alias* used in advertising data
was the hostname. The app therefore filtered out the device and showed nothing or
showed it under the hostname instead of "Moonboard A".

For weeks, the symptom was attributed to "BLE connectivity issues" and various
workarounds (watchdogs, retry loops, bluetoothd `--experimental` flag, mgmt API
manipulation) were attempted. None worked. The actual fix is a single
`btmgmt name "Moonboard A"` call before the BLE peripheral starts.

## What Changes

- **`ble/moonboard_ble_peripheral.service`**: add `ExecStartPre=/usr/bin/btmgmt name "Moonboard A" "MBA"`
  so the BLE adapter advertises with the name the iOS app expects.

## Capabilities

### Modified Capabilities

- `ble-protocol`: Adapter alias is now guaranteed to be "Moonboard A" before
  the GATT advertisement is registered. The iOS Moonboard app can discover the
  device reliably without any post-deploy manual intervention.

## Impact

- `ble/moonboard_ble_peripheral.service` — one new `ExecStartPre` line.
- No code changes required in `moonboard_ble_peripheral.py`.
- Persistent across reboots (re-applied on every service start).
- BlueZ runs in default (non-`--experimental`) mode, unchanged.
