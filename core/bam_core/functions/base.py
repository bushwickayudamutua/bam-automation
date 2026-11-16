from typing import Any

from pydantic import BaseModel, ValidationError


class Function(BaseModel):
    """
    A reusable class for building Digital Ocean Functions
    """

    def run(self) -> Any:
        raise NotImplementedError

    @classmethod
    def run_do(cls, event: dict[str, Any], _context, /):
        """
        The Digital Ocean Function Handler.
        """
        try:
            params = cls.model_validate(event)
        except ValidationError as e:
            return {
                "status": 400,
                "error": e.errors(),
            }
        return {"status": 200, "body": params.run()}

    @classmethod
    def run_cli(cls):
        """
        The CLI handler
        """
        try:
            from pydantic_settings import CliApp
        except ImportError:
            raise RuntimeError(
                "Must install dev dependency pydantic-settings to run function in CLI mode"
            )

        CliApp.run(cls).run()
