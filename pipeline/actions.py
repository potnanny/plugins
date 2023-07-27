import asyncio
import logging
from potnanny.plugins import PipelinePlugin
from potnanny.models.action import Action
from potnanny.models.interface import ObjectInterface


logger = logging.getLogger(__name__)


class ActionPipeline(PipelinePlugin):
    """
    Class to route pipeline measurements to special actions
    """

    name = "Action Pipeline Plugin"
    description = "Route measurements to Actions"

    def __init__(self, *args, **kwargs):
        pass


    async def input(self, measurements):
        tasks = []
        objects = await ObjectInterface(Action).get_all()
        if not objects:
            return

        for obj in objects:
            for m in measurements:

                # pre-filter, only appropriate measurements go to the action
                try:
                    if obj.device_id != m['device_id']:
                        continue

                    if obj.attributes['type'] != m['type']:
                        continue

                    tasks.append(obj.input(m))
                except Exception as x:
                    logger.debug(x)

        if not len(tasks):
            return

        try:
            await asyncio.gather(*tasks)
        except Exception as x:
            logger.warning(x)

