#!/bin/bash
set -euo pipefail

echo "Install services"
cd /home/pi/moonboard

# Install new BLE peripheral service
sudo cp ble/moonboard_ble_peripheral.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable moonboard_ble_peripheral.service

# Install LED service
if [ -f led/moonboard_led.service ]; then
    sudo cp led/moonboard_led.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable moonboard_led.service
fi

echo "Services installed."
