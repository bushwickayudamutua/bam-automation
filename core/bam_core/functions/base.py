from argparse import ArgumentParser
import traceback
import logging
from typing import Any, Dict, List, Optional

from bam_core.lib.airtable import Airtable
from bam_core.lib.mailjet import Mailjet
from bam_core.lib.s3 import S3
from bam_core.lib.google import GoogleMaps
from bam_core.lib.nyc_planning_labs import NycPlanningLabs

log = logging.getLogger(__name__)


class Function(object):
    """
    A reusable class for building Digital Ocean Functions
    """

    mailjet = Mailjet()
    airtable = Airtable()
    s3 = S3()
    gmaps = GoogleMaps()
    nycpl = NycPlanningLabs()

    def __init__(self, parser: Optional[ArgumentParser] = None):
        self.parser = parser or ArgumentParser(
            prog=self.__class__.__name__, description=self.__class__.__doc__
        )

    def add_options(self) -> None:
        """
        Optionally add argparse options to self.parser here
        """
        pass

    def get_options(self) -> Dict[str, Any]:
        """
        Get the params from the parser.
        """
        return vars(self.parser.parse_args())

    def run(self, event, context):
        """
        The core logic of your function.
        """
        raise NotImplementedError

    def main(self, event, context) -> Dict[str, Any]:
        """
        The Digital Ocean Function Handler.
        """
        output = self.run(event, context)
        return {"body": output}

    def cli(self):
        """
        The CLI handler
        """
        self.add_options()
        # override event with options from argparse
        event = self.get_options()
        return self.run(event, {})

    @classmethod
    def run_functions(cls, event, context, *functions) -> Dict[str, Any]:
        """
        Run a list of functions and handle errors
        """
        failures = []
        output = {}
        for function in functions:
            fn = function.__name__
            log.info(f"Running {fn}\n{'*' * 80}")
            try:
                output[fn] = function().main(event, context)
            except Exception as e:
                log.error(f"Error running {fn}")
                log.error(e)
                traceback.print_exc()
                failures.append(fn)
            log.info(f"Finished {fn}\n{'*' * 80}")
        if failures:
            raise Exception(f"Errors running {fn}: {failures}")

        return output
