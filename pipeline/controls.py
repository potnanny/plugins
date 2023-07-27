import asyncio
import logging
from potnanny.plugins import PipelinePlugin
from potnanny.models.control import Control
from potnanny.models.interface import ObjectInterface


logger = logging.getLogger(__name__)


class ControlPipeline(PipelinePlugin):
    """
    Class to route pipeline measurements to controls
    """

    name = "Control Pipeline Plugin"
    description = "Route measurements to device Controls"

    def __init__(self, *args, **kwargs):
        pass


    async def input(self, measurements):
        tasks = []
        controls = await ObjectInterface(Control).get_all()
        if controls is None:
            return

        for c in controls:
            for m in measurements:

                # pre-filter, only appropriate measurements go to the control
                try:
                    if (c.attributes['input_device_id'] != m['device_id']):
                        continue
                    if (c.attributes['type'] != m['type']):
                        continue

                    tasks.append(c.input(m))
                except Exception as x:
                    logger.debug(x)

        if not len(tasks):
            return

        try:
            await asyncio.gather(*tasks)
        except Exception as x:
            logger.warning(x)

