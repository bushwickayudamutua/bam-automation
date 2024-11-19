from argparse import ArgumentDefaultsHelpFormatter, ArgumentParser
import traceback
import logging
from typing import Any, Dict, List, Optional

from bam_core.lib.airtable import Airtable
from bam_core.lib.mailjet import Mailjet
from bam_core.lib.s3 import S3
from bam_core.utils.etc import now_utc
from bam_core.lib.google import GoogleMaps, GoogleSheets
from bam_core.lib.nyc_planning_labs import NycPlanningLabs
from bam_core.functions.params import Params

logger = logging.getLogger(__name__)


class FunctionLogger(object):
    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.log_lines = []

    def _log(self, level, msg):
        self.log_lines.append(
            {"level": level, "message": msg, "time": now_utc()}
        )
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


class Function(object):
    """
    A reusable class for building Digital Ocean Functions
    """

    mailjet = Mailjet()
    airtable = Airtable()
    s3 = S3()
    gmaps = GoogleMaps()
    gsheets = GoogleSheets()
    nycpl = NycPlanningLabs()

    def __init__(self, parser: Optional[ArgumentParser] = None):
        self.parser = parser or ArgumentParser(
            prog=self.__class__.__name__,
            description=self.__class__.__doc__,
            formatter_class=ArgumentDefaultsHelpFormatter,
        )
        self.log = FunctionLogger(self.__class__.__name__)

    @property
    def params(self) -> Params:
        """
        Define the Params for this function.
        """
        return Params()

    @property
    def log_lines(self) -> List[Dict[str, Any]]:
        return self.log.log_lines

    def run(self, params: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        The core logic of your function.
        """
        raise NotImplementedError

    def run_api(self, params: Dict[str, Any]) -> Any:
        """
        The API Handler.
        """
        params = self.params.parse_dict(params)
        return self.run(params, {})

    def run_do(self, event, context) -> Dict[str, Any]:
        """
        The Digital Ocean Function Handler.
        """
        params = self.params.parse_dict(event)
        output = self.run(params, context)
        return {"body": output}

    def run_cli(self):
        """
        The CLI handler
        """
        self.params.add_cli_arguments(self.parser)
        params = self.params.parse_cli_arguments(self.parser)
        return self.run(params, {})

    @classmethod
    def run_do_functions(cls, event, context, *functions) -> Dict[str, Any]:
        """
        Run a list of DO functions and handle errors
        """
        failures = []
        output = {}
        for function in functions:
            fn = function.__name__
            logger.info(f"Running {fn}\n{'*' * 80}")
            try:
                output[fn] = function().run_do(event, context)
            except Exception as e:
                logger.error(f"Error running {fn}")
                logger.error(e)
                traceback.print_exc()
                failures.append(fn)
            logger.info(f"Finished {fn}\n{'*' * 80}")
        if failures:
            raise Exception(f"Errors running {fn}: {failures}")

        return output
