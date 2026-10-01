from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_settings import CliApp

P = TypeVar("P", bound=BaseModel)


class Function(Generic[P]):
    """
    A reusable class for building Digital Ocean Functions
    """

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
