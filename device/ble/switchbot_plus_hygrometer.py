import re
import logging
from potnanny.plugins import BluetoothDevicePlugin
from potnanny.plugins.mixins import FingerprintMixin

logger = logging.getLogger(__name__)

# version 1.1

class SwitchbotPlusHygrometer(BluetoothDevicePlugin, FingerprintMixin):
    """
    Interface with Switchbot Plus Hygrometers.
    """

    name = 'SwitchBot Plus Hygrometer'
    description = "Get values from SwitchBot Plus bluetooth hygrometers"
    reports = ['battery','temperature','humidity']
    fingerprint = {
        'address': re.compile('^E5:83:33', re.IGNORECASE),
        'name': re.compile('^E5-83-33', re.IGNORECASE)
    }

    def __init__(self, *args, **kwargs):
        pass


    def read_advertisement(self, device, advertisement):
        results = {}
        uuid = '0000fd3d-0000-1000-8000-00805f9b34fb'

        logger.debug(advertisement)

        if (hasattr(advertisement, 'service_data') and 
            uuid in advertisement.service_data):
            data = advertisement.service_data[uuid]

            battery = data[2] & 0b01111111
            humidity = data[5] & 0b01111111

            temperature = (data[3] & 0b00001111) / 10 + (data[4] & 0b01111111)
            above_zero = data[4] & 0b10000000
            if not above_zero:
                temperature = -temperature
            
            results = {
                'temperature': temperature,
                'humidity': humidity,
                'battery': battery
            }
        else:
            logger.warning("Unrecognized advertisement data")
            return None

        if self._validate(results):
            return results
        else:
            return None


    def _validate(self, m):
        """
        Validate the measurements. Make sure they are in expected ranges.
        args:
            - dict
        returns:
            Boolean (True if all measurements are valid)
        """

        if (m is None or type(m) is not dict or len(m.keys()) < 1):
            return False

        if ('battery' not in m or 
            m['battery'] is None or 
            m['battery'] < 0 or 
            m['battery'] > 100):
            logger.warning("Invalid battery value %s" % m)
            return False

        if ('temperature' not in m or 
            m['temperature'] is None or 
            m['temperature'] < -20 or 
            m['temperature'] > 60):
            logger.warning("Invalid temperature value %s" % m)
            return False

        if ('humidity' not in m or 
            m['humidity'] is None or 
            m['humidity'] < 0 or 
            m['humidity'] > 100):
            logger.warning("Invalid humidity value %s" % m)
            return False

        return True

