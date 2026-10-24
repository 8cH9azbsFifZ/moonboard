# Design

- Python 3.7 standard library only (`http.server`, `ssl`, `json`) plus the already
  installed `paho-mqtt` 1.6.1 – the Pi Zero W runs Raspbian buster.
- `ThreadingHTTPServer` on `0.0.0.0:8443`, TLS from `/etc/moonboard/tls/server.{crt,key}`.
- Payload equals the LED service message: `START`, `MOVES`, `TOP` required, `LEFT`,
  `FOOT`, `MATCH` optional, positions `A1`…`K18`. Invalid positions are rejected with 400
  instead of being silently ignored by the LED service.
- The service keeps one MQTT connection with automatic reconnect; `/status` reports whether
  it is connected and the last problem shown.
- CORS: the `Origin` is echoed only if it is in the allow-list
  (`MOONBOARD_NET_ORIGINS`, default: PWA server on LAN and Tailscale, the iOS app scheme,
  and the Vite dev server).
- No authentication: the API only switches LEDs in the home network.
