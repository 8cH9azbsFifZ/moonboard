#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HTTPS access to the LED wall over WLAN (openspec/changes/add-wlan-access).

POST /problem  {"START":[..],"MOVES":[..],"TOP":[..], optional "LEFT","FOOT","MATCH"}
POST /clear
GET  /status

Publishes to the MQTT topic the LED service already listens on. Python 3.7, stdlib + paho-mqtt.
"""
import argparse
import json
import logging
import os
import re
import ssl
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "0.1.0"
TOPIC = "moonboard/ble/problem"
REQUIRED = ("START", "MOVES", "TOP")
OPTIONAL = ("LEFT", "FOOT", "MATCH")
POSITION = re.compile(r"^[A-K](?:[1-9]|1[0-8])$")
MAX_BODY = 8192
DEFAULT_ORIGINS = (
    "https://10.101.2.71:8443",
    "https://100.116.179.60:8443",
    "kletterdach://app",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


class InvalidProblem(ValueError):
    pass


def validate_problem(msg):
    """Return a clean problem dict or raise InvalidProblem."""
    if not isinstance(msg, dict):
        raise InvalidProblem("body must be a JSON object")
    clean = {}
    for key in REQUIRED + OPTIONAL:
        if key not in msg:
            if key in REQUIRED:
                raise InvalidProblem("missing key " + key)
            continue
        values = msg[key]
        if not isinstance(values, list):
            raise InvalidProblem(key + " must be a list")
        for pos in values:
            if not isinstance(pos, str) or not POSITION.match(pos):
                raise InvalidProblem("invalid position " + repr(pos) + " in " + key)
        clean[key] = list(values)
    unknown = set(msg) - set(REQUIRED + OPTIONAL)
    if unknown:
        raise InvalidProblem("unknown keys " + ", ".join(sorted(unknown)))
    return clean


def allowed_origin(origin, allowed):
    return origin if origin and origin in allowed else None


class Wall:
    """Holds the MQTT connection and the last shown problem."""

    def __init__(self, host="localhost", port=1883):
        import paho.mqtt.client as paho

        self._lock = threading.Lock()
        self.last = None
        self.connected = False
        self._client = paho.Client(client_id="moonboard-net")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client.connect_async(host, port, keepalive=30)
        self._client.loop_start()

    def _on_connect(self, client, userdata, flags, rc):
        self.connected = rc == 0
        logging.info("MQTT connected rc=%s", rc)

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.warning("MQTT disconnected rc=%s", rc)

    def show(self, problem):
        info = self._client.publish(TOPIC, json.dumps(problem), qos=1)
        info.wait_for_publish()
        with self._lock:
            self.last = {"problem": problem, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    def status(self):
        with self._lock:
            last = self.last
        return {"ok": True, "version": VERSION, "mqtt": self.connected, "last": last}


def make_handler(wall, origins):
    class Handler(BaseHTTPRequestHandler):
        server_version = "moonboard-net/" + VERSION

        def _send(self, code, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        def _cors(self):
            origin = allowed_origin(self.headers.get("Origin"), origins)
            if origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Max-Age", "600")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            if self.path == "/status":
                self._send(200, wall.status())
            else:
                self._send(404, {"ok": False, "error": "not found"})

        def do_POST(self):
            if self.path not in ("/problem", "/clear"):
                self._send(404, {"ok": False, "error": "not found"})
                return
            if self.path == "/clear":
                problem = {"START": [], "MOVES": [], "TOP": []}
            else:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0 or length > MAX_BODY:
                    self._send(400, {"ok": False, "error": "body missing or too large"})
                    return
                try:
                    problem = validate_problem(json.loads(self.rfile.read(length).decode("utf-8")))
                except (ValueError, UnicodeDecodeError) as exc:
                    self._send(400, {"ok": False, "error": str(exc)})
                    return
            if not wall.connected:
                self._send(503, {"ok": False, "error": "LED service bus (MQTT) not connected"})
                return
            wall.show(problem)
            self._send(200, {"ok": True, "shown": problem})

        def log_message(self, fmt, *args):
            logging.info("%s %s", self.address_string(), fmt % args)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8443)
    parser.add_argument("--cert", default="/etc/moonboard/tls/server.crt")
    parser.add_argument("--key", default="/etc/moonboard/tls/server.key")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    env = os.environ.get("MOONBOARD_NET_ORIGINS")
    origins = tuple(o.strip() for o in env.split(",") if o.strip()) if env else DEFAULT_ORIGINS
    wall = Wall(args.mqtt_host)
    httpd = ThreadingHTTPServer((args.bind, args.port), make_handler(wall, origins))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(args.cert, args.key)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    logging.info("listening on https://%s:%s", args.bind, args.port)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
