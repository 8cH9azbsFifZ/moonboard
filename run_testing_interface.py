# -*- coding: utf-8 -*-
import argparse
from led.moonboard import MoonBoard
from functools import partial
import json
import RPi.GPIO as GPIO
import os
#import signal
import sys
import logging
import time
import paho.mqtt.client as paho # FIXME pip install 
import math # floor

# external power LED and power button
LED_GPIO = 26
BUTTON_GPIO = 3


import logging
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


    def _on_message(self, client, userdata, message):
        logging.debug("Received message " + str(message.payload.decode("utf-8")))

        msg = json.loads(message.payload.decode("utf-8"))

        # Check if interval large enough
        time_last = self._time_current 
        self._time_current = time.time()
        del_time = self._time_current - self._time_last
        logging.debug(del_time)
        if del_time < self._update_interval:
            return
        
        self._time_last = time_last

        logging.debug ("Using it")
        #l = "\rLoad: %.1f    " % msg["loadcurrent"]
        #t = "Time: " + str(msg["time"])
        #lmax = "\rLoad Max: %.1f    " % msg["loadmaximal"]
        
        lc = int(msg["loadcurrent"]) 
        lc1 = int(repr(lc)[-1]) 
        lc10 = math.floor(lc/10)
        #lc10 = int(repr(lc)[-2]) 
        #lc100 = int(repr(lc)[-3]) 
        logging.debug("Using: lc10:"+str(lc10))
        logging.debug ("Clean board")
        
        #self._MOONBOARD.clear()
        
        logging.debug ("Begin display holds")
        #charmax = chr(ord('@')+lc1)

        ## 10er
        ymax = 10
        ymin = 1
        ichar = "E"#chr(ord('@')+i1)
        ytmp = ymax - lc10
        color_10er_done = (255,0,0)
        color_10er_not_done = (100,0,0)
        for y in range(ymin,ymax):
            ihold = ichar+str(y)

            if y < ytmp:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[ihold], color_10er_not_done)
            else:
                logging.debug("Use hold "+ihold)
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[ihold], color_10er_done)

        ## 1er
        ichar = "F"#chr(ord('@')+i1)
        ytmp = ymax - lc1
        color_1er_done = (0,255,0)
        color_1er_not_done = (0,100,0)
        for y in range(ymin,ymax):
            ihold = ichar+str(y)

            if y < ytmp:
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[ihold], color_1er_not_done)
            else:
                logging.debug("Use hold "+ihold)
                self._MOONBOARD.layout.set(self._MOONBOARD.MAPPING[ihold], color_1er_done)



            # FIXME: Runs too long - next event occurs....
        self._MOONBOARD.layout.push_to_driver()

        #self._MOONBOARD.show_hold("A4")
        #self._MOONBOARD.show_hold("B4")


    def _record_data(self, hostname="localhost",port=1883):
        logging.debug("Start recording data from mqtt to database")
        self._client= paho.Client("client-001")  # FIXME
        self._client.on_message=self._on_message
        self._client.connect(hostname,port,60)#connect

        # FIXME: subscribe to all?
        
        self._client.subscribe("hangboard/sensor/load/loadstatus")
        #self._client.subscribe("hangboard/sensor/sensorstatus")
        #self._client.subscribe("hangboard/sensor/lastexercise")
        #self._client.subscribe("hangboard/workout/userstatistics")
        #self._client.subscribe("hangboard/workout/upcoming")

        self._client.loop_forever()

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

    parser.add_argument('--debug',  action = "store_true")

    args = parser.parse_args()
    argsd=vars(args)
    logger = logging.getLogger('run')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    #problems
    led_layout = args.led_mapping
    driver_type = args.driver_type

    d = Database(driver_type=driver_type, led_layout=led_layout)
    d._record_data(hostname="raspi-hangboard")   
