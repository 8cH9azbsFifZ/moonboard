# What I (the assistant) Got Wrong

This is an honest post-mortem of my debugging errors during the 24-hour
session on 2026-06-06 / 2026-06-07. The actual fix was a one-line
`ExecStartPre`. I made it into a multi-commit, two-revert, watchdog-engineering
saga because I made the following mistakes:

## 1. I Did Not Check The Obvious First
`btmgmt info` showed `name raspi-moonboard` from the **first minute** of debugging.
I noticed it. I did not connect it to the symptom "phone cannot find Moonboard A".
I never asked the user the most basic question:

> "When you scan, what device names DO you see?"

If I had asked this on hour one, the user would have answered "raspi-moonboard"
and we would have been done in 5 minutes. Instead, I assumed the symptom was
"device invisible" rather than "device visible under wrong name". Three orders of
magnitude in wasted effort came from skipping this one question.

## 2. I Built A Watchdog Before Understanding The Problem
Without any evidence that "advertising goes stale", I designed and implemented
~250 lines of watchdog logic:
- `_check_advertising_active()` (two different implementations, both broken)
- `_recover_advertising()` with unregister + re-register cycles
- 30-second health check timer
- Force re-advertise after disconnect
- Proactive refresh every 2 minutes
- Exponential backoff for repeated failures

None of it was justified by a measurement. All of it had to be reverted.
The watchdog's false positives actively made the system **less stable** than
doing nothing.

**Rule for next time**: Do not write recovery code until I can demonstrate, with
a deterministic test, the failure mode the code is supposed to recover from.

## 3. I Added `--experimental` Without Reading The Code
The Python peripheral code has a fallback path:
```python
try:
    ad_manager.RegisterAdvertisement(...)
except dbus.exceptions.DBusException as e:
    self.logger.warning('LEAdvertisingManager1 not available')
    self._setup_hcitool_advertising()
```
I never noticed this. I assumed "BlueZ 5.50 needs `--experimental` for
`LEAdvertisingManager1`" was the diagnosis, when in fact:
- `LEAdvertisingManager1` works fine without `--experimental` on this BlueZ build
- Adding `--experimental` made the fallback path unreachable
- The fallback (raw `hcitool`) was what had been working before

**Rule for next time**: Read the relevant code paths before changing system config.

## 4. I Modified The Pi Without Tracking
During the session I edited:
- `/lib/systemd/system/bluetooth.service` (added `--experimental`)
- `/etc/bluetooth/main.conf` (added DiscoverableTimeout etc.)
- `/etc/systemd/system/moonboard_ble_peripheral.service` (added `--debug`)
- `/var/lib/bluetooth/B8:27:EB:78:4B:E9/settings` (wrote new content)
- Deleted `/var/lib/bluetooth/B8:27:EB:78:4B:E9/` entirely
- Pushed 6 watchdog commits to `/home/pi/moonboard`

I did not keep a written checklist. When I had to undo the changes, I had to
recall them from memory and from grep'ing `find -mtime -3`. I missed
`--debug` on the moonboard service for several iterations.

**Rule for next time**: For any debugging session that touches persistent system
state, maintain a `STATE-CHANGES.md` from minute zero. Every system mutation gets
appended. At the end, walk the file in reverse to undo everything.

## 5. Confirmation Bias On Each Restart
Every time `btmgmt info` showed `advertising` in current settings, I told the user
"it should work now, try it". When they said "still doesn't work", I went **deeper**
into BlueZ internals instead of stepping back. The `advertising` mgmt flag had
nothing to do with the user's symptom (the name was wrong). I kept looking at the
wrong signal because it had stronger correlation with my expectation than with
reality.

**Rule for next time**: When the user reports the fix didn't work, do not assume
they did the test wrong. Assume the diagnosis was wrong.

## 6. I Missed The User's Decisive Hint
At hour ~23, the user said:
> "ich finde wieder etwas. aber nicht das moonboard a, sondern nur raspi-moon"

(translation: "I find something again. But not Moonboard A, only raspi-moon")

This was the answer. The chip *was* advertising. The name was wrong. The user
had explicitly told me what name the phone could see. I extracted the right
diagnosis from this sentence in ~30 seconds. I should have asked for exactly
this information at minute zero.

## 7. Batched Changes Without Per-Change Verification
I would make 3-5 changes in one command (config edits + service restarts +
btmgmt commands), then ask the user to test. When the test failed I could
not isolate which change had what effect. This made every iteration ambiguous
and forced me to keep cycling.

**Rule for next time**: One change at a time. Measure each change's effect
with btmon or btmgmt info before adding the next change.

## 8. No Baseline Snapshot
I never recorded the system state BEFORE I started changing things. When the
user said "it was working yesterday", I had nothing to compare to. I had no
diff to read. I had to reconstruct "original state" from git history and from
my own (lossy) memory of which files I had touched.

**Rule for next time**: First action in any debug session is a state snapshot:
- `systemctl status <relevant services>`
- All config files I might touch (`cat` + record to a file)
- `journalctl -u <service> -n 200` baseline
- Git revision and worktree status
- For BLE specifically: `btmgmt info`, `hciconfig hci0`, `bluetoothctl show`,
  `ls /var/lib/bluetooth/<addr>/`

## Remaining Stability Concerns (NOT solved by this fix)

The adapter-name fix solves *discoverability*. It does NOT necessarily solve
underlying stability issues that may resurface. Specifically:

1. **`current settings` sometimes lacks `advertising`** — we never understood
   when or why this happens. The chip can be in this state at boot. A future
   debug session may need to investigate the actual BlueZ state machine here.

2. **Disconnect/reconnect cycle** — we did not test sustained operation
   (the user originally reported "after a few route changes, it disconnects").
   This was the original symptom and may not be fixed.

3. **The mgmt API's silent failure** — `Add Advertising` returning success
   without subsequent HCI commands. We saw this happen but did not understand
   the trigger condition.

4. **iOS pairing cache** — we wiped `/var/lib/bluetooth/<addr>/` mid-session.
   The phone's pairing record was not cleared on the iOS side. This mismatch
   may cause future reconnection issues. User should "Forget Device" if
   problems return.

A follow-up debugging session is needed for these. Doing it requires:
- A reliable reproducer for each symptom
- btmon captures of the failing transitions
- A clean "do nothing reactive" approach (no watchdogs)
