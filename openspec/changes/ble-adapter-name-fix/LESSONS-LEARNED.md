# Lessons Learned — BLE Adapter Name Bug

**Period**: 2026-06-06 to 2026-06-07
**Root cause** (found at the end, after many wrong turns):
The BlueZ adapter alias was the Pi's hostname (`raspi-moonboard`) instead of `Moonboard A`.
The iOS Moonboard app filters scan results by name and silently drops anything not called
"Moonboard A".
**Actual fix**: one line — `ExecStartPre=/usr/bin/btmgmt name "Moonboard A" "MBA"` in the
service file.
**Time wasted before finding it**: ~24 hours, many commits, two reverts, several reboots.

This document records everything we tried that did NOT solve the problem, so future
debugging sessions don't waste time on the same dead ends.

---

## The Actual Symptom (correctly interpreted)

- Phone could not find "Moonboard A" in the BLE device list
- Phone sometimes saw a device called "raspi-moonboard" or "raspi-moon" (truncated hostname)
- Phone could not connect to the (renamed) device

The decisive observation came at the very end: the user said "ich finde nicht das Moonboard A,
sondern nur raspi-moon". This was the hint that the chip *was* advertising, just under
the wrong name. The Moonboard app filters by name and ignored everything else.

## Why We Misdiagnosed It For Hours

- Initial framing was "BLE connection hanging" — interpreted as a stability problem
- `btmon` showed `Add Advertising` returning success with `Name (complete): Moonboard A` in
  the scan response — we assumed the device was correctly advertising as "Moonboard A"
- We did not realise that the *advertising data* (separate from scan response) uses the
  *adapter alias*, which was the hostname
- `btmgmt info` did show `name raspi-moonboard` from the start — we noticed but did not
  connect it to the symptom
- We jumped to mgmt-level diagnostics, watchdogs, `--experimental` flags, and chip resets
  before checking the obvious "is the device name right?"

## What We Tried That Did NOT Work

### Attempt 1: `--experimental` flag on bluetoothd
- Added `--experimental` to `/lib/systemd/system/bluetooth.service` ExecStart
- Reasoning: BlueZ 5.50 marks `LEAdvertisingManager1` as experimental
- Result: No change in behaviour. Removed.

### Attempt 2: BLE advertising watchdog (6 commits, all reverted in `8d717ba`)
- `_check_advertising_active()` using `hcitool` HCI probe → returned 0x0C (Command Disallowed)
- `_check_advertising_active()` using D-Bus `ActiveInstances` → false positives
- `_recover_advertising()` doing UnregisterApplication + RegisterApplication
- Periodic health check every 30s
- Force re-advertise after every disconnect
- Proactive advertisement refresh every 2 minutes
- **Result**: Made the situation worse. Repeated unregister/re-register cycles
  put the chip into inconsistent states. All reverted.

### Attempt 3: `btmgmt connectable on / discov on / advertising on`
- Worked when service was stopped, failed when service was running
- Did not persist across reboots
- **Result**: No effect on actual visibility from the phone.

### Attempt 4: Writing `Discoverable=true` to `/var/lib/bluetooth/<addr>/settings`
- bluetoothd ignored the file changes
- **Result**: No effect.

### Attempt 5: `/etc/bluetooth/main.conf` with `DiscoverableTimeout = 0`
- Combined with btmgmt commands, all settings flags showed correctly
- Phone still could not find the board
- **Result**: Restored original main.conf.

### Attempt 6: Deleting `/var/lib/bluetooth/<adapter>/` entirely
- Wiped all paired-device state
- bluetoothd recreated the directory on restart
- **Result**: No change in advertising behaviour. (Probably also unhelpful: lost the existing pairing.)

### Attempt 7: Direct HCI commands via `hcitool` while bluetoothd was stopped
- All HCI LE commands returned status 0x00 (Success)
- `btmon` showed the commands going to the controller
- Did not complete an end-to-end test because we kept moving on to other things
- **Result**: Inconclusive. May have actually worked if we had tested.

### Attempt 8: Restart `hciuart` to reload BCM firmware
- `sudo systemctl restart hciuart`
- `btuart` timed out trying to re-init the BCM chip
- Required a full Pi reboot to recover
- **Result**: Do not do this. Hung the chip.

### Attempt 9: Power cycle the Pi (hard reboot)
- After reboot, same broken state
- **Result**: Confirmed the issue is in the config, not chip residual state.

## Diagnostic Findings That Are Still Valuable

1. **Chip LE radio works**: `btmgmt find` successfully scans nearby BLE devices.
   If you ever doubt the chip, run this first.

2. **HCI commands are blocked when bluetoothd manages the adapter**: All
   `hcitool cmd 0x08 0x...` for LE return 0x0C while bluetoothd is running.
   Must stop bluetoothd first to issue raw LE commands.

3. **btmon shows what was actually advertised**:
   ```
   @ MGMT Command: Add Advertising (0x003e) plen 42
           Instance: 1
           Flags: 0x00000003
           Advertising data length: 18
           128-bit Service UUIDs (complete): 1 entry
             Nordic UART Service
           Scan response length: 13
           Name (complete): Moonboard A   <-- in scan response only
   ```
   The local name "Moonboard A" was in the SCAN RESPONSE. The ADVERTISING DATA
   used the adapter alias (the hostname). Different scanners look at different
   fields. The Moonboard iOS app evidently filters on the advertising data name.

4. **`Failed to set privacy: Rejected (0x0b)`** in bluetoothd startup: the BCM43438
   does not support LE Privacy. This is harmless noise, not the cause of any issue.

## Generic Lessons

- **Verify the obvious things first.** When the symptom is "the device cannot be found",
  check the broadcast name *before* diving into HCI traces and chip firmware theories.
- **`btmgmt info` is the source of truth** for adapter-level state. Read it carefully —
  the name field told us the answer from minute one.
- **Watchdogs make broken systems worse**, not better, if the watchdog's "health check"
  is unreliable. A watchdog that fires false positives causes more downtime than the
  problem it tries to fix.
- **Document failed attempts as you go.** This file should have been started on hour one,
  not at the end. Future-you (or future-coworker) will thank you.
- **The Pi state survives reboots.** If you modify `/lib/systemd/`, `/etc/bluetooth/`,
  `/var/lib/bluetooth/`, or the deployed code, document it and clean it up. Power cycles
  do not undo persistent filesystem changes.
