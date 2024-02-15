import re
import logging
import asyncio
import datetime
from bleak import BleakClient
from potnanny.plugins.base import BluetoothDevicePlugin
from potnanny.plugins.mixins import FingerprintMixin


logger = logging.getLogger(__name__)

# version 1.1

class PacketManager:
    """
    Class for manipulating and validating data packets from BLE device
    """

    def __init__(self, *args, **kwargs):
        self.default_sz = 20
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)


    def validate(self, data, size=None, contains_chksum=True):
        """
        Validate a byte array. Ensure proper length and chksum
        args:
            - bytearray
            - expected size of data, minus chksum (optional)
            - is final byte of the array an XOR chksum to be validated?
        returns:
            - Bool
        """

        if size is None:
            size = self.default_sz

        if type(data) != bytearray:
            logger.warning("Data is not bytearray (%s) %s" % (type(data), data))
            return False

        if len(data) != size:
            logger.warning("Data incorrect length (%d) %s" % (len(data), data))
            return False

        if contains_chksum:
            check = data[-1]
            chksum = self.get_checksum(data[:(size - 1)])
            if chksum != check:
                logger.warning("Data checksum wrong (%d) %s" % (chksum, data))
                return False

        return True


    def get_checksum(self, data):
        """
        Do an XOR of all bytes to get a checksum of the data
        args:
            bytearray
        returns:
            int
        """

        chksum = 0
        for val in data:
            chksum ^= val

        return chksum


    def build(self, data, size=None, add_chksum=True):
        """
        Build a bytearray of the proper length. Zeros are padded to the end.
        args:
            - bytearray
            - size of final packet buffer (int)
            - Final byte should be checksum of previous bytes?
        returns:
            bytearray
        """

        if size is None:
            size = self.default_sz

        if len(data) < size:
            data += bytearray([0 for i in range(0, (size - len(data)))])

        if add_chksum:
            chksum = self.get_checksum(data[:(size - 1)])
            data[-1] = chksum

        return data


class H5082Code:
    STATE = bytearray(b'\xaa\x01')
    FIRMWARE = bytearray(b'\xaa\x06')
    HARDWARE = bytearray(b'\xaa\x07\x03')
    SWITCH = bytearray(b'\x33\x01')
    ON1 = bytearray(b'\x23')
    OFF1 = bytearray(b'\x20')
    ON2 = bytearray(b'\x11')
    OFF2 = bytearray(b'\x10')
    WAIT_SECRET = bytearray(b'\xaa\xb1')
    HAS_SECRET = bytearray(b'\xaa\xb1\x01')
    send_key = bytearray(b'\x33\xb2')


class GoveeH5082(BluetoothDevicePlugin, FingerprintMixin):
    """

    For the H5080, there is only one outlet. And it is labeled outlet_1.
    For the H5082, outlet_1 is the LEFT outlet. outlet_2 is the RIGHT.

         1         2
    ---------------------
    |  I   I     I   I  |
    |    o         o    |
    ---------------------
            H5082

    """

    name = 'Govee H5082'
    description = "Control Govee H5082 bluetooth power outlet"
    reports = ['outlet_1', 'outlet_2']
    fingerprint = {
        'name': re.compile(r'^ihoment_H5082', re.IGNORECASE),
    }

    def __init__(self, *args, **kwargs):
        self.address = None
        self.key_code = None
        self._state = None
        self._auto_disconnect = True
        self._default_packet_sz = 20
        self._tx = '00010203-0405-0607-0809-0a0b0c0d2b11'
        self._rx = '00010203-0405-0607-0809-0a0b0c0d2b10'
        self._client = None
        self._packet = PacketManager(default_sz=20)

        allowed = ['address', 'key_code']
        for k, v in kwargs.items():
            if hasattr(self, k) and k in allowed:
                setattr(self, k, v)

        if self.address is None:
            raise ValueError("Need a device address")


    async def connect(self):
        """
        Connect client to device
        """

        if self._client is None:
            self._client = BleakClient(self.address)

        if not self._client.is_connected:
            await self._client.connect()


    async def disconnect(self):
        """
        Disconnect client
        """

        try:
            await self._client.disconnect()
        except:
            pass


    def read_advertisement(self, device, advertisement):
        results = None
        key = 34818
        if key not in advertisement.manufacturer_data:
            return results

        bufr = advertisement.manufacturer_data[key]
        value = int(bufr[-1])
        try:
            if re.search(r'H5082', advertisement.local_name, re.IGNORECASE):
                results = {
                    'outlet_2': value & 1,
                    'outlet_1': (value >> 1) & 1 }
            else:
                results = {'outlet_1': value}
        except Exception as x:
            logger.warning(x)

        return results


    async def on(self, outlet:int = 1):
        """
        Switch device outlet ON
        """

        rval = await self.set_state(outlet, 1)
        return rval


    async def off(self, outlet:int = 1):
        """
        Switch device outlet OFF
        """

        rval = await self.set_state(outlet, 0)
        return rval


    async def set_state(self, outlet:int, value:int):
        await self.connect()

        if bool(value) is True:
            if outlet == 2:
                code = H5082Code.ON2
            else:
                code = H5082Code.ON1
        else:
            if outlet == 2:
                code = H5082Code.OFF2
            else:
                code = H5082Code.OFF1

        payload = self._packet.build(
            bytearray(H5082Code.SWITCH + code)
        )

        tries = 2
        found = False
        def handler(sender, data):
            nonlocal found
            if data[:2] == H5082Code.STATE:
                tmp = int(bool(data[2]))
                if tmp == value:
                    self._state = int(bool(data[2]))
                    found = True

        await self._client.start_notify(self._rx, handler)
        while tries and not found:
            await self.send_key()
            await self._client.write_gatt_char(self._tx, payload)

            await asyncio.sleep(0.6)
            tries -= 1

        try:
            await self._client.stop_notify(self._rx)
            if self._auto_disconnect:
                await self.disconnect()
        except Exception as x:
            logger.warning("Error disconnecting from device: %s" % x);

        self._state = value
        return self._state


    async def scan_key(self):
        """
        listen for device secret key code when button is pushed
        """

        found = False
        def handler(sender, data):
            nonlocal found
            if not self._packet.validate(data):
                # skip invalid packets
                return

            if data[:3] == H5082Code.HAS_SECRET:
                if self.key_code is None:
                    self.key_code = [int(i) for i in data[3:11]]
                    found = True


        if self.key_code is None:
            await self.connect()
            payload = self._packet.build(bytearray(H5082Code.WAIT_SECRET))
            await self._client.start_notify(self._rx, handler)
            # tries = (self.ATTEMPTS * 4)
            tries = 8
            while not found and tries:
                try:
                    await self._client.write_gatt_char(self._tx, bytearray(payload))
                except:
                    pass
                finally:
                    await asyncio.sleep(1)
                    tries -= 1

            try:
                await self._client.stop_notify(self._rx)
            except:
                pass

            if self._auto_disconnect:
                await self.disconnect()

        return self.key_code


    async def send_key(self):
        """
        Send secret key code to device, for authorization to switch state
        """

        if self.key_code is None:
            raise ValueError("No secret to tell")

        payload = self._packet.build(
            bytearray(
                H5082Code.send_key + bytearray(self.key_code)))
        await self._client.write_gatt_char(self._tx, payload)

