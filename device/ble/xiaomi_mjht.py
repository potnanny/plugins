import re
import asyncio
import logging
import random
from bleak import BleakClient
from potnanny.plugins import BluetoothDevicePlugin
from potnanny.plugins.mixins import FingerprintMixin

logger = logging.getLogger(__name__)

# version 1.1

class XiaomiMJHT(BluetoothDevicePlugin, FingerprintMixin):
    name = 'Xiaomi MJHT Hygrometer'
    description = "Get values from Xiaomi MJHT Hygrometer"
    reports = ['temperature', 'humidity']
    fingerprint = {
        'address': re.compile(r'^4C:65:A8', re.IGNORECASE),
        'name': re.compile(r'^MJ_HT', re.IGNORECASE)
    }


    def __init__(self, *args, **kwargs):
        self.address = None
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        if self.address is None:
            raise ValueError('Plugin requires device mac address')


    async def poll(self):
        values = None
        async with BleakClient(self.address) as client:
            try:
                values = await self._read_measurements(client)
                await client.disconnect()
            except Exception as x:
                logger.debug(x)

        return values


    async def _read_measurements(self, client):
        uuid = '226caa55-6476-4566-7562-66734470666d'
        bufr = None
        tries = 10
        values = None

        def callback(sender, data):
            nonlocal bufr
            bufr = data

        await client.start_notify(uuid, callback)
        while tries > 0:
            if bufr:
                tries = 0
                break
            await asyncio.sleep(0.5)
            tries -= 1

        await client.stop_notify(uuid)

        if bufr:
            text = bufr.decode()
            match = re.match(r'T=(\d+\.\d+)\s+H=(\d+\.\d+)', text)
            if match:
                values = {
                    'temperature': float(match.group(1)),
                    'humidity': float(match.group(2)) }

        return values

