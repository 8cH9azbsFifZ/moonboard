# -*- coding: utf-8 -*-
"""
Moonboard BLE Peripheral Service (v2)

Proper BlueZ D-Bus GATT server implementing Nordic UART Service (NUS).
Replaces the fragile btmon-sniffing approach.

Key improvements over legacy:
- Proper WriteValue callback (no btmon parsing)
- write-without-response support for iOS/Android
- TX characteristic present (required by some NUS clients)
- BlueZ LEAdvertisingManager1 for advertising (no raw hcitool)
- Per-device protocol state (multi-phone safe)
- Non-blocking WriteValue with queue-based processing
- Auto-restart advertising on disconnect

Requires:
- BlueZ >= 5.50 (Raspbian Buster)
- bluetoothd running (optionally with --experimental for LEAdvertisingManager1)
- D-Bus permissions for com.moonboard (see com.moonboard.conf)
"""

import sys
import os
import json
import logging
import queue
import threading
import signal

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

from moonboard_app_protocol import UnstuffSequence, decode_problem_string

try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except ImportError:
    HAS_MQTT = False

# BlueZ D-Bus constants
BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

# Nordic UART Service UUIDs
NUS_SERVICE_UUID = '6e400001-b5a3-f393-e0a9-e50e24dcca9e'
NUS_RX_UUID = '6e400002-b5a3-f393-e0a9-e50e24dcca9e'
NUS_TX_UUID = '6e400003-b5a3-f393-e0a9-e50e24dcca9e'

# Configuration defaults
DEFAULT_ADAPTER = '/org/bluez/hci0'
DEFAULT_LOCAL_NAME = 'Moonboard A'
DEFAULT_MQTT_HOST = 'localhost'
DEFAULT_MQTT_PORT = 1883
MQTT_TOPIC_PROBLEM = 'moonboard/ble/problem'
MQTT_TOPIC_STATUS = 'moonboard/ble/status'


class Advertisement(dbus.service.Object):
    """BLE advertisement using BlueZ LEAdvertisingManager1 D-Bus API."""

    PATH_BASE = '/org/bluez/moonboard/advertisement'

    def __init__(self, bus, index, logger):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.logger = logger
        self.ad_type = 'peripheral'
        self.local_name = DEFAULT_LOCAL_NAME
        self.service_uuids = [NUS_SERVICE_UUID]
        self.include_tx_power = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        properties['LocalName'] = dbus.String(self.local_name)
        properties['ServiceUUIDs'] = dbus.Array(self.service_uuids, signature='s')
        properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface)
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='',
                         out_signature='')
    def Release(self):
        self.logger.info('Advertisement released')


class NUSService(dbus.service.Object):
    """Nordic UART GATT Service with RX (write) and TX (notify) characteristics."""

    PATH_BASE = '/org/bluez/moonboard/service'

    def __init__(self, bus, index, logger):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.logger = logger
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': NUS_SERVICE_UUID,
                'Primary': True,
                'Characteristics': dbus.Array(
                    [c.get_path() for c in self.characteristics],
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, chrc):
        self.characteristics.append(chrc)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface)
        return self.get_properties()[GATT_SERVICE_IFACE]


class RXCharacteristic(dbus.service.Object):
    """NUS RX Characteristic - receives data from the Moonboard app.
    
    Supports both 'write' and 'write-without-response' to handle
    all iOS/Android BLE write modes.
    """

    def __init__(self, bus, index, service, rx_queue, logger):
        self.path = service.get_path() + '/char' + str(index)
        self.bus = bus
        self.uuid = NUS_RX_UUID
        self.service = service
        self.rx_queue = rx_queue
        self.logger = logger
        self.flags = ['write', 'write-without-response']
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s'),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}',
                         out_signature='')
    def WriteValue(self, value, options):
        """Handle incoming BLE write from Moonboard app.
        
        Non-blocking: enqueues raw bytes for processing by worker thread.
        """
        raw_bytes = bytes(value)
        device = str(options.get('device', 'unknown'))
        self.logger.debug(f'RX [{device}]: {raw_bytes.hex()} ({len(raw_bytes)}B)')
        self.rx_queue.put_nowait((raw_bytes, device))

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface)
        return self.get_properties()[GATT_CHRC_IFACE]


class TXCharacteristic(dbus.service.Object):
    """NUS TX Characteristic - notify-capable (required by NUS clients).
    
    The Moonboard app expects this characteristic to exist even if
    we never send notifications. Without it, some iOS versions refuse
    to connect or discover the service properly.
    """

    def __init__(self, bus, index, service, logger):
        self.path = service.get_path() + '/char' + str(index)
        self.bus = bus
        self.uuid = NUS_TX_UUID
        self.service = service
        self.logger = logger
        self.flags = ['notify']
        self.notifying = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': dbus.Array(self.flags, signature='s'),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='', out_signature='')
    def StartNotify(self):
        self.notifying = True
        self.logger.debug('TX: StartNotify')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='', out_signature='')
    def StopNotify(self):
        self.notifying = False
        self.logger.debug('TX: StopNotify')

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise dbus.exceptions.DBusException(
                'org.freedesktop.DBus.Error.InvalidArgs',
                'Invalid interface: ' + interface)
        return self.get_properties()[GATT_CHRC_IFACE]


class GATTApplication(dbus.service.Object):
    """BlueZ GATT Application containing the NUS service."""

    PATH = '/org/bluez/moonboard'

    def __init__(self, bus, rx_queue, logger):
        self.path = self.PATH
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

        # Create NUS service with RX and TX characteristics
        nus = NUSService(bus, 0, logger)
        rx_chrc = RXCharacteristic(bus, 0, nus, rx_queue, logger)
        tx_chrc = TXCharacteristic(bus, 1, nus, logger)
        nus.add_characteristic(rx_chrc)
        nus.add_characteristic(tx_chrc)
        self.services.append(nus)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.characteristics:
                response[chrc.get_path()] = chrc.get_properties()
        return response


class MoonboardBLEPeripheral:
    """Main controller: manages BLE GATT, advertising, protocol decoding, and MQTT."""

    def __init__(self, adapter=DEFAULT_ADAPTER, mqtt_host=DEFAULT_MQTT_HOST,
                 mqtt_port=DEFAULT_MQTT_PORT, logger=None):
        self.adapter = adapter
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.logger = logger or logging.getLogger('moonboard.ble')
        self.rx_queue = queue.Queue()
        self.unstuffers = {}  # per-device protocol state
        self.loop = None
        self._mqtt_client = None
        self._use_hcitool_fallback = False

    def start(self):
        """Initialize and run the BLE peripheral."""
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        # Setup MQTT
        if HAS_MQTT:
            self._setup_mqtt()

        # Register GATT application
        self.logger.info('Registering GATT application...')
        self.app = GATTApplication(bus, self.rx_queue, self.logger)

        adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, self.adapter)

        # Register GATT
        gatt_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
        gatt_manager.RegisterApplication(
            self.app.get_path(), {},
            reply_handler=self._register_app_cb,
            error_handler=self._register_app_error_cb)

        # Register Advertisement (try BlueZ LEAdvertisingManager1 first)
        try:
            ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)
            self.adv = Advertisement(bus, 0, self.logger)
            ad_manager.RegisterAdvertisement(
                self.adv.get_path(), {},
                reply_handler=self._register_ad_cb,
                error_handler=self._register_ad_error_cb)
        except dbus.exceptions.DBusException as e:
            self.logger.warning(f'LEAdvertisingManager1 not available: {e}')
            self.logger.warning('Falling back to hcitool advertising (deprecated)')
            self._use_hcitool_fallback = True
            self._setup_hcitool_advertising()

        # Start RX processing worker thread
        self._rx_worker = threading.Thread(target=self._process_rx_loop,
                                           daemon=True, name='rx-worker')
        self._rx_worker.start()

        # Monitor device disconnects to cleanup state and re-advertise
        bus.add_signal_receiver(
            self._on_properties_changed,
            signal_name='PropertiesChanged',
            dbus_interface=DBUS_PROP_IFACE,
            path_keyword='path')

        # Run main loop
        self.loop = GLib.MainLoop()
        self.logger.info('Moonboard BLE Peripheral running...')
        if HAS_MQTT:
            self._publish_status('running')

        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.logger.info('Interrupted')
        finally:
            self.loop.quit()
            if HAS_MQTT and self._mqtt_client:
                self._publish_status('stopped')
                self._mqtt_client.disconnect()

    def _setup_mqtt(self):
        """Connect to MQTT broker with reconnect and retry."""
        self._mqtt_client = mqtt.Client(client_id='moonboard-ble')
        self._mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        max_retries = 10
        for attempt in range(1, max_retries + 1):
            try:
                self._mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
                self._mqtt_client.loop_start()
                self.logger.info(f'MQTT connected to {self.mqtt_host}:{self.mqtt_port}')
                return
            except Exception as e:
                self.logger.warning(f'MQTT connect attempt {attempt}/{max_retries} failed: {e}')
                if attempt < max_retries:
                    import time
                    time.sleep(min(attempt * 2, 15))
        self.logger.error('MQTT connection failed after all retries, continuing without MQTT')

    def _publish_status(self, status):
        if self._mqtt_client:
            self._mqtt_client.publish(MQTT_TOPIC_STATUS, status)

    def _publish_problem(self, problem):
        if self._mqtt_client:
            msg = json.dumps(problem)
            self._mqtt_client.publish(MQTT_TOPIC_PROBLEM, msg)
            self.logger.info(f'Published problem: {msg}')

    def _process_rx_loop(self):
        """Worker thread: processes incoming BLE data from the queue."""
        while True:
            try:
                raw_bytes, device = self.rx_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            try:
                self._handle_rx(raw_bytes, device)
            except Exception as e:
                self.logger.error(f'Error processing RX from {device}: {e}')

    def _handle_rx(self, raw_bytes, device):
        """Process raw bytes from a BLE write, using per-device protocol state."""
        # Get or create per-device unstuffer
        if device not in self.unstuffers:
            self.unstuffers[device] = UnstuffSequence(self.logger)
            self.logger.info(f'New device connected: {device}')

        unstuffer = self.unstuffers[device]

        # Convert raw bytes to hex string for the existing protocol parser
        hex_str = raw_bytes.hex()
        new_problem_string = unstuffer.process_bytes(hex_str)
        flags = unstuffer.flags

        if new_problem_string is not None:
            problem = decode_problem_string(new_problem_string, flags)
            self.logger.info(f'Problem decoded: {problem}')
            self._publish_problem(problem)
            unstuffer.flags = []

    def _setup_hcitool_advertising(self):
        """Fallback: setup BLE advertising via raw hcitool HCI commands.
        
        Used only when BlueZ LEAdvertisingManager1 is not available.
        """
        import subprocess
        self.logger.info('Setting up hcitool advertising...')
        cmds = [
            "hcitool -i hci0 cmd 0x08 0x000a 00",
            "hcitool -i hci0 cmd 0x08 0x0008 18 02 01 06 02 0a 00 11 07 "
            "9e ca dc 24 0e e5 a9 e0 93 f3 a3 b5 01 00 40 6e 00 00 00 00 00 00 00",
            "hcitool -i hci0 cmd 0x08 0x0009 0d 0c 09 4d 6f 6f 6e 62 6f 61 72 64 20 41",
            "hcitool -i hci0 cmd 0x08 0x0006 80 02 c0 03 00 00 00 00 00 00 00 00 00 07 00",
            "hcitool -i hci0 cmd 0x08 0x000a 01",
        ]
        for cmd in cmds:
            try:
                subprocess.run(["sudo"] + cmd.split(),
                               check=True, capture_output=True, timeout=5)
            except subprocess.CalledProcessError as e:
                self.logger.error(f'hcitool command failed: {cmd} → {e.stderr}')
            except subprocess.TimeoutExpired:
                self.logger.error(f'hcitool command timed out: {cmd}')

    def _restart_advertising_on_disconnect(self):
        """Re-enable hcitool advertising after a device disconnects (fallback mode)."""
        if getattr(self, '_use_hcitool_fallback', False):
            self.logger.info('Re-enabling hcitool advertising after disconnect')
            self._setup_hcitool_advertising()

    def _on_properties_changed(self, interface, changed, invalidated, path=''):
        """Handle BlueZ device property changes (disconnect detection)."""
        if interface != 'org.bluez.Device1':
            return
        if 'Connected' in changed and not changed['Connected']:
            self.logger.info(f'Device disconnected: {path}')
            # Cleanup stale protocol state
            self.unstuffers.pop(path, None)
            # Re-enable advertising in fallback mode
            self._restart_advertising_on_disconnect()

    def _register_app_cb(self):
        self.logger.info('GATT application registered')

    def _register_app_error_cb(self, error):
        self.logger.error(f'Failed to register GATT application: {error}')
        if self.loop:
            self.loop.quit()

    def _register_ad_cb(self):
        self.logger.info('Advertisement registered')

    def _register_ad_error_cb(self, error):
        self.logger.warning(f'Failed to register advertisement: {error}')
        self.logger.warning('Falling back to hcitool advertising')
        self._use_hcitool_fallback = True
        self._setup_hcitool_advertising()


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Moonboard BLE Peripheral Service')
    parser.add_argument('--adapter', default=DEFAULT_ADAPTER,
                        help='BlueZ adapter path (default: /org/bluez/hci0)')
    parser.add_argument('--mqtt-host', default=DEFAULT_MQTT_HOST,
                        help='MQTT broker hostname (default: localhost)')
    parser.add_argument('--mqtt-port', type=int, default=DEFAULT_MQTT_PORT,
                        help='MQTT broker port (default: 1883)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    args = parser.parse_args()

    # Setup logging
    logger = logging.getLogger('moonboard.ble')
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(name)s [%(levelname)s] %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if args.debug else logging.INFO)

    # Run peripheral
    peripheral = MoonboardBLEPeripheral(
        adapter=args.adapter,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        logger=logger
    )

    signal.signal(signal.SIGTERM, lambda *_: peripheral.loop.quit() if peripheral.loop else sys.exit(0))
    peripheral.start()


if __name__ == '__main__':
    main()
