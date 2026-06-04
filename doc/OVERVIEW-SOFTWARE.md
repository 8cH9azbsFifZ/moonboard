# Overview - Software used in this project


## Software Build Instructions

* Flash a fresh Raspian buster (or newer)
* run installer
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/8cH9azbsFifZ/moonboard/master/install/install.sh)"
```

## Architecture

The system consists of two independent services communicating via MQTT:

```
[Moonboard App] --BLE--> [BLE Peripheral Service] --MQTT--> [LED Service] --SPI/GPIO--> [WS2811 LEDs]
```

### BLE Peripheral Service (`ble/moonboard_ble_peripheral.py`)
- Implements a proper BlueZ D-Bus GATT server with Nordic UART Service (NUS)
- Receives problem data via BLE WriteValue callback
- Decodes the Moonboard protocol (packet unstuffing, hold parsing)
- Publishes decoded problems as JSON to MQTT

### LED Service (`led/moonboard_led_service.py`)
- Subscribes to MQTT topic `moonboard/ble/problem`
- Drives WS2811/WS2801 LED strips via BiblioPixel
- Displays holds in color: START=green, MOVES=blue, LEFT=violet, FOOT=cyan, MATCH=pink, TOP=red

### MQTT Topics

| Topic | Direction | Format |
|-------|-----------|--------|
| `moonboard/ble/problem` | BLE → LED | `{"START":["A1"],"MOVES":["C5"],"LEFT":[],"FOOT":[],"MATCH":[],"TOP":["K18"],"FLAGS":["D"]}` |
| `moonboard/ble/status` | BLE → monitor | `running` / `stopped` |

## Configuration

Copy `config.yaml.example` to `config.yaml` and adjust for your installation.
Key settings: MQTT broker, LED driver type, LED mapping file, brightness.

## Services (systemd)

| Service | File | Description |
|---------|------|-------------|
| BLE Peripheral | `ble/moonboard_ble_peripheral.service` | BLE GATT + advertising |
| LED Display | `led/moonboard_led.service` | MQTT subscriber + LED driver |

### Service Management
```bash
# Stop/restart services
sudo systemctl restart moonboard_ble_peripheral.service
sudo systemctl restart moonboard_led.service

# View logs
journalctl -fu moonboard-ble
journalctl -fu moonboard-led
```

## Troubleshooting

### BLE Connection Issues
1. **App can't find "Moonboard A"**: Check `bluetoothctl show` — adapter must be powered on. Run `sudo bluetoothctl power on`.
2. **LEAdvertisingManager1 not available**: Enable experimental mode: edit `/lib/systemd/system/bluetooth.service`, add `--experimental` to `ExecStart`.
3. **Multiple phones crash the service**: The new peripheral service handles per-device state. Only one problem is displayed at a time (last write wins).
4. **Service needs restart after reboot**: Run `scripts/fix_startup.sh` or check service ordering with `systemctl list-dependencies`.

### LED Issues
1. **No LEDs light up**: Check `led_mapping.json` matches your wiring. Use `--driver_type SimPixel` for testing without hardware.
2. **Wrong holds illuminated**: Verify LED_SPACING and mapping with `led/create_nth_led_layout.py`.

## Legacy Files (deprecated)

| File | Replaced by |
|------|------------|
| `run.py` | `led/moonboard_led_service.py` |
| `ble/moonboard_ble_service.py` | `ble/moonboard_ble_peripheral.py` |
| `ble/moonboard_ble_dbus_service.py` | `ble/moonboard_ble_peripheral.py` |

## LED Driver

The LED driver uses BiblioPixel with support for:
- **PiWS281x**: WS2811 via GPIO/PWM (recommended)
- **WS2801**: via SPI `/dev/spidev0.1`
- **SimPixel**: Browser-based simulator for development

## Animations

Run `led/animations.py` for special effects:
```bash
python3 led/animations.py --mode silvester   # Silvester fireworks show
python3 led/animations.py --mode firework    # Single fireworks
python3 led/animations.py --mode watermelon  # Pixel art
python3 led/animations.py --mode wipe        # Color wipe
python3 led/animations.py --mode solid --color 255,0,255  # Solid color
```

## Docker version
+ Install docker `curl -fsSL https://get.docker.com -o get-docker.sh` and `sudo sh get-docker.sh`