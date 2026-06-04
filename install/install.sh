#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Moonboard Installation ==="

# Apply bluetooth patch for iPhone compatibility
echo "Applying BlueZ override for iPhone BLE..."
sudo mkdir -p /etc/systemd/system/bluetooth.service.d
cat <<EOF | sudo tee /etc/systemd/system/bluetooth.service.d/moonboard.conf
[Service]
ExecStart=
ExecStart=/usr/lib/bluetooth/bluetoothd --experimental -P battery
EOF
sudo systemctl daemon-reload
sudo systemctl restart bluetooth

# Install system dependencies
echo "Installing system packages..."
sudo apt-get -y install bluetooth bluez python3-dbus python3-gi mosquitto mosquitto-clients

# Install Python dependencies
echo "Installing Python packages..."
pip3 install -r "$SCRIPT_DIR/requirements.txt"

# Install services
"$SCRIPT_DIR/30-install-services.sh"

echo ""
echo "Installation complete. Reboot recommended."
