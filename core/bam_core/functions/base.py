import logging
import traceback
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_settings import CliApp

logger = logging.getLogger(__name__)

P = TypeVar("P", bound=BaseModel)


class Function(Generic[P]):
    """
    A reusable class for building Digital Ocean Functions
    """

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    param_model: type[P]

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
