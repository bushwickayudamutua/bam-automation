from argparse import ArgumentParser
from typing import Any, Dict, Optional

from bam_core.lib.airtable import Airtable
from bam_core.lib.mailjet import Mailjet
from bam_core.lib.s3 import S3


class Function(object):
    """
    A reusable class for building Digital Ocean Functions
    """

    mailjet = Mailjet()
    airtable = Airtable()
    s3 = S3()

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
