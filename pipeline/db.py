import asyncio
import logging
from potnanny.database import db, lock
from potnanny.plugins import PipelinePlugin
from potnanny.models.measurement import Measurement, MeasurementSchema


logger = logging.getLogger(__name__)


class DBPipeline(PipelinePlugin):
    """
    Class to save measurements to the potnanny database
    """

    name = "Database Insert Plugin"
    description = "Insert measurements to Potnanny database"


    async def input(self, measurements):
        """
        Accept measurments input, and insert into db

        args:
            - list of measurement dicts
        returns:
            none
        """

        schema = MeasurementSchema(many=True)
        clean = schema.load(measurements)

        async with lock:
            async with db.transaction():
                for m in clean:
                    try:
                        obj = await Measurement.create(**m)
                    except Exception as x:
                        logger.debug(x)


