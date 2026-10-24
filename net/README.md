# WLAN access

Small HTTPS API that lights problems on the wall without Bluetooth
(`openspec/changes/add-wlan-access`). It publishes to the MQTT topic the LED service
already listens on.

```bash
curl --cacert ca.crt -X POST https://10.101.40.13:8443/problem \
  -H 'Content-Type: application/json' \
  -d '{"START":["A1"],"MOVES":["F9"],"TOP":["K18"]}'
curl --cacert ca.crt -X POST https://10.101.40.13:8443/clear
curl --cacert ca.crt https://10.101.40.13:8443/status
```

## Install on the Pi

1. Certificate for the Pi's address from the household's private CA (the one the
   iPhones/iPads already trust), as `/etc/moonboard/tls/server.crt` and `server.key`
   (key readable by user `pi`). Never commit them.
2. `sudo cp net/moonboard_net.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable --now moonboard_net`

Allowed CORS origins can be overridden with `MOONBOARD_NET_ORIGINS` (comma separated).
