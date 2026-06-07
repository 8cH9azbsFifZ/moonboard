# Tasks

## 1. Service File: Adapter Name Fix

- [x] 1.1 Add `ExecStartPre=/usr/bin/btmgmt name "Moonboard A" "MBA"` to `ble/moonboard_ble_peripheral.service` before the main ExecStart
- [x] 1.2 Verify the change survives reboots (ExecStartPre runs on every service start)

## 2. Deploy and Verify

- [x] 2.1 Deploy updated service file to `/etc/systemd/system/moonboard_ble_peripheral.service` on raspi-moonboard
- [x] 2.2 Restart moonboard_ble_peripheral service
- [x] 2.3 Confirm `btmgmt info` shows `name Moonboard A` and `short name MBA`
- [x] 2.4 User-tested: iOS Moonboard app finds and connects to the board

## 3. Documentation

- [x] 3.1 Update CHANGELOG.md with v1.1.0 entry
- [x] 3.2 Create LESSONS-LEARNED.md documenting what we tried that did NOT work
- [x] 3.3 Tag release v1.1.0
