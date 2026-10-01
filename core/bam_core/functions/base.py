import logging
import traceback
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_settings import CliApp

from bam_core.functions.params import Params
from bam_core.lib.airtable import Airtable
from bam_core.lib.dialpad import Dialpad
from bam_core.lib.google import GoogleMaps, GoogleSheets
from bam_core.lib.mailjet import Mailjet
from bam_core.lib.nyc_planning_labs import NycPlanningLabs
from bam_core.lib.s3 import S3
from bam_core.utils.etc import now_utc

logger = logging.getLogger(__name__)

P = TypeVar("P", bound=BaseModel)

class FunctionLogger:
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.log_lines = []

    def _log(self, level, msg):
        self.log_lines.append({"level": level, "message": msg, "time": now_utc()})
        getattr(self.logger, level)(msg)

    def info(self, msg):
        self._log("info", msg)

    def error(self, msg):
        self._log("error", msg)

    def exception(self, msg):
        self._log("exception", msg)

    def debug(self, msg):
        self._log("debug", msg)

    def warning(self, msg):
        self._log("warning", msg)


class Function(Generic[P]):
    """
    A reusable class for building Digital Ocean Functions
    """

    mailjet = Mailjet()
    airtable = Airtable()
    s3 = S3()
    gmaps = GoogleMaps()
    gsheets = GoogleSheets()
    nycpl = NycPlanningLabs()

    def __init__(self):
        self.log = FunctionLogger(self.__class__.__name__)
        self.dialpad = Dialpad(logger=self.log)

    param_model: type[P]

    @property
    def log_lines(self) -> list[dict[str, Any]]:
        return self.log.log_lines

    def run(self, _params: P, /):
        raise NotImplementedError

    def run_do(self, event: dict[str, Any], _context, /):
        """
        The Digital Ocean Function Handler.
        """
        try:
            params = self.param_model.model_validate(event)
        except ValidationError as e:
            return {
                "status": 400,
                "error": e.errors(),
            }
        return {"status": 200, "body": self.run(params)}

    def run_cli(self):
        """
        The CLI handler
        """
        return self.run(CliApp.run(self.param_model))

    @classmethod
    def run_do_functions(cls, event, *functions) -> dict[str, Any]:
        """
        Run a list of DO functions and handle errors
        """
        failures = []
        output = {}
        for function in functions:
            fn = function.__name__
            logger.info(f"Running {fn}\n{'*' * 80}")
            try:
                output[fn] = function().run_do(event)
            except Exception as e:
                logger.error(f"Error running {fn}")
                logger.error(e)
                traceback.print_exc()
                failures.append(fn)
            logger.info(f"Finished {fn}\n{'*' * 80}")
        if failures:
            raise Exception(f"Errors running {fn}: {failures}")

        return output
