#!/bin/bash
for s in moonboard_led.service moonboard_ble.service; do
sudo systemctl restart $s
done
