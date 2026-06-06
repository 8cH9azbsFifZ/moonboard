Deploy Moonboard changes to the Raspberry Pi. Use when the user says "deploy", "auf den Raspi", "remote update", "ausrollen", or when code changes need to be pushed to the Moonboard hardware.

## Steps

1. **Ensure changes are committed and pushed**
   - Check `git status` for uncommitted changes
   - If uncommitted: stage, commit (NO Co-authored-by trailer, NEVER mention Copilot), and push
   - If already pushed: skip

2. **Run deploy script**
   ```bash
   cd /Users/gerolfziegenhain/src/moonboard
   bash scripts/deploy.sh raspi-moonboard master
   ```
   The script handles:
   - SSH connectivity check
   - Git fetch + checkout on Raspi
   - Python dependency install
   - bluetoothd `--experimental` flag enforcement
   - systemd service install + restart (bluetooth → moonboard_ble_peripheral → moonboard_led)
   - Post-deploy health check

3. **Verify deployment**
   After deploy.sh completes, SSH to raspi and verify:
   ```bash
   ssh pi@raspi-moonboard "journalctl -u moonboard_ble_peripheral --since '1 min ago' --no-pager | tail -10"
   ```
   Confirm:
   - "GATT application registered"
   - "Advertisement registered"
   - "Advertising watchdog started"

4. **Report result**
   Show deployed version and service status to the user.

## Important

- **NEVER** include `Co-authored-by: Copilot` or any mention of Copilot in commit messages
- Host: `raspi-moonboard`, User: `pi`, Remote dir: `/home/pi/moonboard`
- Default branch/target: `master`
- The Raspi runs Raspbian Buster with BlueZ 5.50 and Python 3.7
- Services: `moonboard_ble_peripheral.service`, `moonboard_led.service`
- bluetoothd MUST have `--experimental` flag

## Quick deploy (if user just wants to push current state)

```bash
cd /Users/gerolfziegenhain/src/moonboard
git add -A && git commit -m "<meaningful message>" && git push origin master
bash scripts/deploy.sh raspi-moonboard master
```

## Troubleshooting

If deploy fails:
1. Check SSH: `ssh pi@raspi-moonboard "echo ok"`
2. Check services: `ssh pi@raspi-moonboard "sudo systemctl status moonboard_ble_peripheral"`
3. Check logs: `ssh pi@raspi-moonboard "journalctl -u moonboard_ble_peripheral -n 30 --no-pager"`
4. Nuclear option: `ssh pi@raspi-moonboard "sudo hciconfig hci0 reset && sudo systemctl restart bluetooth && sleep 3 && sudo systemctl restart moonboard_ble_peripheral"`
