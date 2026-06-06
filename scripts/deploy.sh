#!/bin/bash
set -euo pipefail

# Deploy Moonboard to Raspberry Pi
# Usage: ./scripts/deploy.sh [host] [tag/branch]
#   host:   default "raspi-moonboard"
#   target: default "main" (tag or branch name)

HOST="${1:-raspi-moonboard}"
TARGET="${2:-main}"
USER="pi"
REMOTE_DIR="/home/${USER}/moonboard"
SSH=(ssh "-o" "ConnectTimeout=10" "-l${USER}" "${HOST}")

echo "╔══════════════════════════════════════╗"
echo "║   Moonboard Deploy → ${HOST}"
echo "║   Version: ${TARGET}"
echo "╚══════════════════════════════════════╝"
echo ""

# 0. SSH connectivity check
echo "▶ Checking connectivity..."
if ! "${SSH[@]}" "true" 2>/dev/null; then
    echo "ERROR: Cannot reach ${HOST} via SSH"
    exit 1
fi
echo "  ✓ SSH connection OK"

# 1. Pre-flight check
echo ""
echo "▶ Pre-flight check..."
"${SSH[@]}" "test -d ${REMOTE_DIR}/.git" || { echo "ERROR: ${REMOTE_DIR} is not a git repo"; exit 1; }
echo "  ✓ Remote repo exists"

# 2. Fetch & checkout target version
echo ""
echo "▶ Fetching and checking out ${TARGET}..."
"${SSH[@]}" "cd ${REMOTE_DIR} && git fetch --tags origin && git checkout ${TARGET} && git pull origin ${TARGET} 2>/dev/null || true"
echo "  ✓ Checked out ${TARGET}"

# 3. Show what version is deployed
echo ""
echo "▶ Deployed version:"
"${SSH[@]}" "cd ${REMOTE_DIR} && git log --oneline -1"

# 4. Install Python dependencies
echo ""
echo "▶ Checking dependencies..."
"${SSH[@]}" "cd ${REMOTE_DIR} && if [ -f install/requirements.txt ]; then pip3 install -r install/requirements.txt; echo '  ✓ pip deps installed'; else echo '  ⊘ no requirements.txt'; fi"

# 5. Install system packages needed for BLE/MQTT
echo ""
echo "▶ Checking system packages..."
"${SSH[@]}" "dpkg -s mosquitto python3-dbus python3-gi >/dev/null 2>&1 && echo '  ✓ system deps OK' || { echo '  Installing system deps...'; sudo apt-get -y install bluetooth bluez python3-dbus python3-gi mosquitto mosquitto-clients; }"

# 6. Fix bluetoothd configuration (ensure --experimental flag)
echo ""
echo "▶ Checking bluetoothd configuration..."
"${SSH[@]}" bash -s << 'BTFIX'
BT_SERVICE="/lib/systemd/system/bluetooth.service"
if grep -q '\-\-experimental' "$BT_SERVICE"; then
    echo "  ✓ bluetoothd --experimental already set"
else
    echo "  → Adding --experimental to bluetoothd..."
    sudo sed -i 's|^ExecStart=/usr/lib/bluetooth/bluetoothd|ExecStart=/usr/lib/bluetooth/bluetoothd --experimental|' "$BT_SERVICE"
    sudo systemctl daemon-reload
    echo "  ✓ bluetoothd --experimental configured"
fi
BTFIX

# 7. Install/update systemd services
echo ""
echo "▶ Installing systemd services..."

# BLE peripheral
"${SSH[@]}" "cd ${REMOTE_DIR} && if [ -f ble/moonboard_ble_peripheral.service ]; then
    sudo cp ble/moonboard_ble_peripheral.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable moonboard_ble_peripheral.service 2>/dev/null || true
    echo '  ✓ moonboard_ble_peripheral.service installed'
fi"

# LED service
"${SSH[@]}" "cd ${REMOTE_DIR} && if [ -f led/moonboard_led.service ]; then
    sudo cp led/moonboard_led.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable moonboard_led.service 2>/dev/null || true
    echo '  ✓ moonboard_led.service installed'
fi"

# 8. Restart services (correct order: bluetooth first, then moonboard)
echo ""
echo "▶ Restarting services..."

# Stop old BLE services first
for svc in moonboard_ble com.moonboard; do
    "${SSH[@]}" "sudo systemctl stop ${svc}.service 2>/dev/null; sudo systemctl disable ${svc}.service 2>/dev/null || true"
done
echo "  ✓ Legacy BLE services stopped"

# Restart bluetooth stack first (needed for --experimental to take effect)
"${SSH[@]}" "sudo systemctl stop moonboard_ble_peripheral.service 2>/dev/null || true"
"${SSH[@]}" "sudo systemctl restart bluetooth.service"
echo "  ✓ bluetooth.service restarted"
sleep 3

# Start moonboard services
for svc in moonboard_ble_peripheral moonboard_led; do
    "${SSH[@]}" "if systemctl is-enabled ${svc}.service &>/dev/null; then
        sudo systemctl restart ${svc}.service
        sleep 1
        STATUS=\$(systemctl is-active ${svc}.service)
        echo \"  ${svc}: \${STATUS}\"
    else
        echo \"  ${svc}: not installed\"
    fi"
done

# 9. Health check with verification
echo ""
echo "▶ Health check..."
sleep 4
HEALTH_OK=true

"${SSH[@]}" "systemctl is-active moonboard_led.service &>/dev/null && echo '  ✓ LED service running' || echo '  ✗ LED service NOT running'"
if ! "${SSH[@]}" "systemctl is-active moonboard_ble_peripheral.service &>/dev/null"; then
    echo "  ✗ BLE peripheral NOT running"
    HEALTH_OK=false
else
    echo "  ✓ BLE peripheral running"
fi

# Verify advertisement registered
if "${SSH[@]}" "journalctl -u moonboard_ble_peripheral --since '30 sec ago' --no-pager 2>/dev/null | grep -q 'Advertisement registered'"; then
    echo "  ✓ BLE advertisement registered"
else
    echo "  ⚠ BLE advertisement not confirmed (may need more time)"
fi

# Verify watchdog started
if "${SSH[@]}" "journalctl -u moonboard_ble_peripheral --since '30 sec ago' --no-pager 2>/dev/null | grep -q 'watchdog started'"; then
    echo "  ✓ Advertising watchdog active"
else
    echo "  ⚠ Watchdog not confirmed yet"
fi

"${SSH[@]}" "mosquitto_pub -t test -m ping 2>/dev/null && echo '  ✓ MQTT broker reachable' || echo '  ⚠ MQTT broker not responding'"

echo ""
if [ "$HEALTH_OK" = true ]; then
    echo "═══════════════════════════════════════"
    echo "  ✓ Deploy complete! Test with Moonboard app."
    echo "═══════════════════════════════════════"
else
    echo "═══════════════════════════════════════"
    echo "  ⚠ Deploy complete but health check has warnings."
    echo "  Check: journalctl -u moonboard_ble_peripheral -f"
    echo "═══════════════════════════════════════"
    exit 1
fi
