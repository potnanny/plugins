import re
import logging
import asyncio
from bleak import BleakClient
from potnanny.plugins import BluetoothDevicePlugin
from potnanny.plugins.mixins import FingerprintMixin

logger = logging.getLogger(__name__)

# version 1.1

class MiFlora(BluetoothDevicePlugin, FingerprintMixin):
    name = 'Xiaomi Soil Sensor'
    description = "Get values from Xiaomi Mi Flora bluetooth soil sensor"
    reports = ['battery','temperature','light','soil_ec','soil_moisture']
    fingerprint = {
        'address': re.compile(r'^C4:7C:8D', re.IGNORECASE),
        'name': re.compile(r'flower\s+(care|mate)', re.IGNORECASE)
    }

    def __init__(self, *args, **kwargs):
        self.address = None
        allowed = ['address']
        for k, v in kwargs.items():
            if hasattr(self, k) and k in allowed:
                setattr(self, k, v)

        if self.address is None:
            msg = "%s. Need a device address" % self.name
            logger.warning(msg)
            raise ValueError(msg)


    async def poll(self):
        values = None
        async with BleakClient(self.address) as client:
            try:
                values = await self._read_values(client)
                if values:
                    await client.disconnect()
            except Exception as x:
                logger.warning(x)

        return values


    async def _read_values(self, client):
        results = {}
        battery, firmware = await self._read_battery_firmware(client)
        if firmware >= '2.6.6':
            await self._write_mode_change(client)

        results = await self._read_measurement_data(client)
        if results is not None:
            results['battery'] = battery

        if self._validate(results) is False:
            results = {}

        return results


    async def _read_battery_firmware(self, client):
        """
        Read battery and firmware values
        args:
            none
        returns:
            tuple (battery:int, firmware:str)
        """

        uuid = '00001a02-0000-1000-8000-00805f9b34fb'
        data = await client.read_gatt_char(uuid)
        return (data[0], data[2:].decode())


    async def _write_mode_change(self, client):
        """
        Write data to characteristic, to force device to populate measurements.
        args:
            none
        returns:
            none
        """

        uuid = '00001a00-0000-1000-8000-00805f9b34fb'
        mc = b'\xa0\x1f'
        await client.write_gatt_char(uuid, mc)


    async def _read_measurement_data(self, client):
        """
        Read the 16-byte measurement block from the sensor.
        """

        uuid = '00001a01-0000-1000-8000-00805f9b34fb'
        data = await client.read_gatt_char(uuid)
        if len(data) == 16:
            return self._decode_measurements(data)
        else:
            return None


    def _decode_measurements(self, data):
        results = {
            'light': 0,
            'temperature': 0,
            'soil_moisture': 0,
            'soil_ec': 0 }

        def parse_temp(buf):
            t = int.from_bytes(buf[0:2], byteorder='little')
            return t/10.0

        def parse_light(buf):
            l = int.from_bytes(buf[3:7], byteorder='little')
            return l

        def parse_moisture(buf):
            m = buf[7]
            return m

        def parse_ec(buf):
            c = int.from_bytes(buf[8:10], byteorder='little')
            return c

        if len(data) == 16:
            results['temperature'] = parse_temp(data)
            results['light'] = parse_light(data)
            results['soil_moisture'] = parse_moisture(data)
            results['soil_ec'] = parse_ec(data)

        return results


    def _validate(self, m):
        """
        Validate the measurements. Make sure they are in expected ranges.
        args:
            - dict
        returns:
            Boolean (True if all measurements are valid)
        """

        if m is None:
            return False

        if 'battery' not in m or \
            m['battery'] is None or \
            m['battery'] < 0 or \
            m['battery'] > 100:
            logger.warning("Invalid battery value %s" % m)
            return False

        if 'temperature' not in m or \
            m['temperature'] is None or \
            m['temperature'] < -30 or \
            m['temperature'] > 60:
            logger.warning("Invalid temperature value %s" % m)
            return False

        if 'light' not in m or \
            m['light'] is None or \
            m['light'] < 0 or \
            m['light'] > 30000:
            logger.warning("Invalid light value %s" % m)
            return False

        if 'soil_moisture' not in m or \
            m['soil_moisture'] is None or \
            m['soil_moisture'] < 0 or \
            m['soil_moisture'] > 100:
            logger.warning("Invalid soil_moisture value %s" % m)
            return False

        if 'soil_ec' not in m or \
            m['soil_ec'] is None or \
            m['soil_ec'] < 0 or \
            m['soil_ec'] > 5000:
            logger.warning("Invalid soil_ec value %s" % m)
            return False

        return True

