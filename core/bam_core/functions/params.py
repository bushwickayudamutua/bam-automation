import json
from datetime import datetime
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Any, Dict, List, Union

from bam_core.utils.serde import json_to_obj
from bam_core.utils.etc import to_bool


class ParamType:
    name = "base"

    def validate(self, value: Any) -> Any:
        raise NotImplementedError

    def validate_cli(self, value: str) -> Any:
        return self.validate(value)

    def parse(self, value: Any) -> Any:
        if value is None:
            return None
        return self.validate(value)

    def parse_cli(self, value: Any) -> Any:
        if value is None:
            return None
        return self.validate_cli(value)


class ParamIntType(ParamType):
    name = "int"

    def validate(self, value: Any) -> int:
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"Expected int, got {value}")


class ParamFloatType(ParamType):
    name = "float"

    def validate(self, value: Any) -> float:
        try:
            return float(value)
        except ValueError:
            raise ValueError(f"Expected float, got {value}")


class ParamDatetimeType(ParamType):
    name = "datetime"

    def validate(self, value: Any) -> datetime:
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            raise ValueError(f"Expected datetime in ISO format, got {value}")


class ParamJsonType(ParamType):
    name = "json"

    def validate(self, value: Any) -> Union[list, dict]:
        if isinstance(value, str):
            try:
                return json_to_obj(value)
            except json.JSONDecodeError:
                raise ValueError(f"Expected JSON-string, got {value}")
        if not isinstance(value, (list, dict)):
            raise ValueError(f"Expected list or dict, got {value}")
        return value


class ParamStringType(ParamType):
    name = "string"

    def validate(self, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError(f"Expected str, got {value}")
        return value.strip()

    def validate_cli(self, value: str) -> str:
        return self.validate(value)


class ParamBoolType(ParamType):
    name = "bool"

    def validate(self, value: Any) -> bool:
        try:
            return to_bool(value)
        except:
            raise ValueError(f"Expected bool, got {value}")

    def validate_cli(self, value: str) -> bool:
        return self.validate(value)


class ParamStringListType(ParamType):
    sub_type = ParamStringType()

    @property
    def name(self):
        return f"{self.sub_type.name}_list"

    def validate(self, value: Any) -> list:
        if not isinstance(value, list):
            value = [value]
        return [self.sub_type.validate(v) for v in value]

    def validate_cli(self, value: str) -> list:
        try:
            return [self.sub_type.validate(v) for v in value.split(",")]
        except Exception as e:
            raise ValueError(
                f"Expected comma-separated list of {self.sub_type.name} values, got {value}. Error: {e}"
            )


class ParamIntListType(ParamStringListType):
    sub_type = ParamIntType()


class ParamFloatListType(ParamStringListType):
    sub_type = ParamFloatType()


class ParamDatetimeListType(ParamStringListType):
    sub_type = ParamDatetimeType()


class ParamBoolListType(ParamStringListType):
    sub_type = ParamBoolType()


PARAM_TYPES = (
    ParamStringType,
    ParamIntType,
    ParamFloatType,
    ParamDatetimeType,
    ParamBoolType,
    ParamStringListType,
    ParamIntListType,
    ParamFloatListType,
    ParamDatetimeListType,
    ParamBoolListType,
    ParamJsonType,
)

PARAM_TYPES_MAP = {str(t().name): t for t in PARAM_TYPES}


@dataclass
class Param:
    name: str
    type: Union[str, ParamType] = ParamStringType()
    default: Any = None
    description: str = ""
    required: bool = False

    @property
    def short_name(self) -> str:
        words = self.name.split("_")
        if len(words) > 1:
            return "".join([w[0].lower() for w in words])
        return self.name[:2]

    @property
    def name_upper(self) -> str:
        return self.name.upper()

    @property
    def type_class(self) -> ParamType:
        if isinstance(self.type, PARAM_TYPES):
            return self.type
        if isinstance(self.type, str):
            if self.type not in PARAM_TYPES_MAP:
                raise ValueError(
                    f"Unsupported parameter type: {self.type}. Choose from: {', '.join([str(t.name) for t in PARAM_TYPES])}"
                )
            return PARAM_TYPES_MAP[self.type]()
        raise ValueError(f"Unsupported parameter type: {self.type}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type.name,
            "default": self.default,
            "description": self.description,
            "required": self.required,
        }


class Params:
    def __init__(self, *params: List[Union[Param, Dict[str, Any]]]):
        self.params = {}
        for param in params:
            self.add_param(param)

    def add_param(self, param: Union[Param, Dict[str, Any]]):
        if isinstance(param, dict):
            param = Param(**param)
        if not isinstance(param.type_class, PARAM_TYPES):
            raise ValueError(
                f"Unsupported parameter type: {param.type_class}. Choose from: {', '.join([str(t.name) for t in PARAM_TYPES])}"
            )
        self.params[param.name] = param

    def add_cli_arguments(self, parser: ArgumentParser) -> None:
        """
        Add parameters as CLI arguments to the provided parser
        Args:
            parser: the ArgumentParser instance
        """
        for param in self.params.values():
            args = [
                f"-{param.short_name}",
                f"--{param.name.replace('_', '-')}",
            ]
            kwargs = {
                "type": param.type_class.parse_cli,
                "help": f"{param.type_class.name}: " + param.description,
                "required": param.required,
            }
            if not param.required:
                kwargs["default"] = param.default
            parser.add_argument(*args, **kwargs)

    def parse_cli_arguments(self, parser: ArgumentParser) -> Dict[str, Any]:
        """
        Parse CLI arguments using the provided parser
        """
        return vars(parser.parse_args())

    def parse_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a dictionary of parameters
        Args:
            data: the dictionary of raw parameters
        Returns:
            a dictionary of parsed parameters
        """
        parsed_params = {}
        for param in self.params.values():
            value = data.get(
                param.name, data.get(param.name_upper, param.default)
            )
            if value is None and param.required:
                raise ValueError(f"Missing required parameter: {param.name}")
            try:
                value = param.type_class.parse(value)
            except Exception as e:
                raise ValueError(f"Error parsing parameter {param.name}: {e}")
            parsed_params[param.name] = value
        return parsed_params

    def parse_json(self, json_input: str) -> Dict[str, Any]:
        """
        Parse a JSON string of parameters
        Args:
            json_input: the JSON string of raw parameters
        Returns:
            a dictionary of parsed parameters
        """
        data = json_to_obj(json_input)
        return self.parse_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """
        Format the parameters as a dictionary
        """
        return {param.name: param.to_dict() for param in self.params.values()}
