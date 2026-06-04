#!/bin/bash
for service in moonboard_led.service moonboard_ble_peripheral.service; do
    sudo systemctl restart "$service"
done
