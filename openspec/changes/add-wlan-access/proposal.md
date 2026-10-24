# Show problems over WLAN instead of Bluetooth

## Why

The BLE emulation of the Moonboard LED box was unreliable in daily use. The own app
KletterDach (private repo) generates and stores problems for this home wall and must
light them directly over the home network, without an intermediate server.

## What Changes

- New service `net/moonboard_net_service.py`: small HTTPS API on the Pi that validates a
  problem and publishes it to the existing MQTT topic `moonboard/ble/problem`. The LED
  service stays unchanged.
- TLS certificate issued by the household's private CA that the iPhones/iPads already
  trust, so a PWA served via HTTPS may call the Pi directly.
- CORS allow-list for the app origins.
- The BLE service is no longer needed (it may stay installed but disabled).

## Capabilities

### New Capabilities
- `wlan-access`: show and clear problems on the wall over HTTPS in the home network

### Modified Capabilities
- none

## Impact

- New systemd unit `moonboard_net.service` (user `pi`, port 8443).
- Certificate files under `/etc/moonboard/tls/` on the Pi, never in the repo.
