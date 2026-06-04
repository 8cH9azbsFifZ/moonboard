# -*- coding: utf-8 -*-
import argparse
from moonboard import MoonBoard
from functools import partial
import json
import RPi.GPIO as GPIO
import os
import sys
import logging
import time
import paho.mqtt.client as paho
import math

# external power LED and power button
LED_GPIO = 26
BUTTON_GPIO = 3


logging.basicConfig(level=logging.DEBUG,
                    format='Display(%(threadName)-10s) %(message)s',
                    )

class Database():
    def __init__(self, driver_type="", led_layout=""):
        self._MOONBOARD = MoonBoard(driver_type, led_layout)

        # Init timers
        self._time_current = time.time()
        self._time_last = self._time_current 
        self._update_interval = 1.0 #0.5 # Update interval for display in seconds


    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logging.info("MQTT connected, subscribing to moonboard/ble/problem")
            client.subscribe("moonboard/ble/problem", qos=1)
        else:
            logging.error(f"MQTT connection failed with rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.warning(f"MQTT unexpected disconnect (rc={rc}), will reconnect")

    def _on_message(self, client, userdata, message):
        try:
            payload = message.payload.decode("utf-8")
        except UnicodeDecodeError:
            logging.error("Invalid UTF-8 in MQTT message, ignoring")
            return

        try:
            msg = json.loads(payload)
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in MQTT message: {payload[:100]}")
            return

        # Validate required keys
        required_keys = ["START", "MOVES", "TOP"]
        for key in required_keys:
            if key not in msg:
                logging.error(f"Missing key '{key}' in problem message")
                return

        logging.debug("Received message " + payload)

        GREEN = (0,255,0)
        BLUE = (0,0,255)
        RED = (255,0,0)
        VIOLET = (180,0,255)
        CYAN = (0,255,255)
        PINK = (255,96,136)

        # Build new frame in memory first, then push once (no flicker)
        self._MOONBOARD.layout.all_off()
        for s in msg["START"]:
            if s in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[s], GREEN)
        for m in msg.get("MOVES", []):
            if m in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[m], BLUE)        
        for t in msg.get("LEFT", []):
            if t in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[t], VIOLET)
        for t in msg.get("FOOT", []):
            if t in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[t], CYAN)
        for t in msg.get("MATCH", []):
            if t in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[t], PINK)
        for t in msg["TOP"]:
            if t in self._MOONBOARD.MAPPING:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[t], RED)
        
        self._MOONBOARD.layout.push_to_driver()



    def _record_data(self, hostname="localhost", port=1883):
        logging.debug("Start recording data from mqtt")
        self._client = paho.Client(client_id="moonboard-led")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)
        # Retry initial connection (broker may not be up at boot)
        max_retries = 20
        for attempt in range(1, max_retries + 1):
            try:
                self._client.connect(hostname, port, 60)
                break
            except Exception as e:
                logging.warning(f"MQTT connect attempt {attempt}/{max_retries}: {e}")
                if attempt < max_retries:
                    time.sleep(min(attempt * 2, 15))
                else:
                    logging.error("MQTT connection failed, exiting")
                    sys.exit(1)
        self._client.loop_forever(retry_first_connection=True)

# Main stuff

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='')

    parser.add_argument('--driver_type',
                        help='driver type, depends on leds and device controlling the led.',
                        choices=['PiWS281x', 'WS2801', 'SimPixel'],
                        default='PiWS281x')

    parser.add_argument('--brightness',  default=100, type=int)

    parser.add_argument('--led_mapping',
                        type=str,  
                        default='led_mapping.json', 
                        )

    parser.add_argument('--mqtt-host', default='localhost',
                        help='MQTT broker hostname (default: localhost)')

    parser.add_argument('--debug',  action = "store_true")

    args = parser.parse_args()
    logger = logging.getLogger('run')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    led_layout = args.led_mapping
    driver_type = args.driver_type

    d = Database(driver_type=driver_type, led_layout=led_layout)
    d._record_data(hostname=args.mqtt_host)   
