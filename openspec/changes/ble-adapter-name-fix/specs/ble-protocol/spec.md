# BLE Protocol — Adapter Name Delta

## ADDED Requirements

### Requirement: Adapter alias matches advertised local name
The system SHALL ensure the BlueZ adapter alias is set to `Moonboard A` before
the GATT advertisement is registered. This SHALL be enforced on every service
start so the BCM43438 controller broadcasts the same device name the Moonboard
iOS app filters for.

#### Scenario: Service start sets adapter alias
- **WHEN** `moonboard_ble_peripheral.service` starts (boot or restart)
- **THEN** `ExecStartPre` runs `btmgmt name "Moonboard A" "MBA"` before the
  Python peripheral process is launched
- **AND** the adapter alias is "Moonboard A" when `RegisterAdvertisement` is called
- **AND** the iOS Moonboard app can discover the device by its expected name
