#!/bin/bash
set -euo pipefail

# Deploy Moonboard to Raspberry Pi
# Usage: ./scripts/deploy.sh [host] [tag/branch]
#   host:   default "raspi-moonboard"
#   target: default "v1.4" (tag or branch name)

HOST="${1:-raspi-moonboard}"
TARGET="${2:-v1.4}"
USER="pi"
REMOTE_DIR="/home/${USER}/moonboard"
SSH="ssh -l${USER} ${HOST}"

echo "╔══════════════════════════════════════╗"
echo "║   Moonboard Deploy → ${HOST}"
echo "║   Version: ${TARGET}"
echo "╚══════════════════════════════════════╝"
echo ""

# 1. Pre-flight check
echo "▶ Pre-flight check..."
${SSH} "test -d ${REMOTE_DIR}/.git" || { echo "ERROR: ${REMOTE_DIR} is not a git repo"; exit 1; }
echo "  ✓ Remote repo exists"

# 2. Fetch & checkout target version
echo ""
echo "▶ Fetching and checking out ${TARGET}..."
${SSH} "cd ${REMOTE_DIR} && git fetch --tags origin && git checkout ${TARGET}"
echo "  ✓ Checked out ${TARGET}"

# 3. Show what version is deployed
echo ""
echo "▶ Deployed version:"
${SSH} "cd ${REMOTE_DIR} && git log --oneline -1"

# 4. Install Python dependencies if requirements exist
echo ""
echo "▶ Checking dependencies..."
${SSH} "cd ${REMOTE_DIR} && if [ -f requirements.txt ]; then pip3 install -q -r requirements.txt 2>/dev/null || true; echo '  ✓ pip deps checked'; else echo '  ⊘ no requirements.txt'; fi"

# 5. Install/update systemd services
echo ""
echo "▶ Installing systemd services..."

# BLE peripheral (new)
${SSH} "cd ${REMOTE_DIR} && if [ -f ble/moonboard_ble_peripheral.service ]; then
    sudo cp ble/moonboard_ble_peripheral.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable moonboard_ble_peripheral.service 2>/dev/null || true
    echo '  ✓ moonboard_ble_peripheral.service installed'
fi"

# LED service
${SSH} "cd ${REMOTE_DIR} && if [ -f install/moonboard_led.service ]; then
    sudo cp install/moonboard_led.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable moonboard_led.service 2>/dev/null || true
    echo '  ✓ moonboard_led.service installed'
fi"

# 6. Restart services
echo ""
echo "▶ Restarting services..."

# Stop old BLE services first
for svc in moonboard_ble com.moonboard; do
    ${SSH} "sudo systemctl stop ${svc}.service 2>/dev/null; sudo systemctl disable ${svc}.service 2>/dev/null || true"
done
echo "  ✓ Legacy BLE services stopped"

# Start new services
for svc in moonboard_ble_peripheral moonboard_led; do
    ${SSH} "if systemctl is-enabled ${svc}.service &>/dev/null; then
        sudo systemctl restart ${svc}.service
        sleep 1
        STATUS=\$(systemctl is-active ${svc}.service)
        echo \"  ${svc}: \${STATUS}\"
    else
        echo \"  ${svc}: not installed\"
    fi"
done

# 7. Health check
echo ""
echo "▶ Health check..."
${SSH} "systemctl is-active moonboard_led.service &>/dev/null && echo '  ✓ LED service running' || echo '  ✗ LED service NOT running'"
${SSH} "systemctl is-active moonboard_ble_peripheral.service &>/dev/null && echo '  ✓ BLE peripheral running' || echo '  ✗ BLE peripheral NOT running (may need old service)'"
${SSH} "mosquitto_pub -t test -m ping 2>/dev/null && echo '  ✓ MQTT broker reachable' || echo '  ⚠ MQTT broker not responding'"

echo ""
echo "═══════════════════════════════════════"
echo "  Deploy complete! Test with Moonboard app."
echo "═══════════════════════════════════════"
