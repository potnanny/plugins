import asyncio
import logging
import potnanny.database as db
from potnanny.locks import LOCKS
from potnanny.plugins import PipelinePlugin
from potnanny.models.measurement import Measurement, MeasurementSchema

logger = logging.getLogger(__name__)


class DBPipeline(PipelinePlugin):
    """
    Class to save measurements to the potnanny database
    """

    name = "Database Insert Plugin"
    description = "Insert measurements to Potnanny database"

    def __init__(self, *args, **kwargs):
        try:
            self.lock = LOCKS['db']
        except:
            self.lock = None


    async def input(self, measurements):
        """
        Accept measurments input, and insert into db

        args:
            - list of measurement dicts
        returns:
            none
        """

        schema = MeasurementSchema(many=True)

        async def db_execute(f):
            if self.lock:
                async with self.lock:
                    await f()
            else:
                await f()

        async def perform():
            try:
                async with db.session() as session:
                    clean = schema.load(measurements)
                    for m in clean:
                        obj = Measurement(**m)
                        session.add(obj)

                    await session.commit()
            except Exception as x:
                logger.warning(x)

        await db_execute(perform)

