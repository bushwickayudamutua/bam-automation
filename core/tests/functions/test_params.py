import pytest
from argparse import ArgumentParser
from datetime import datetime

from bam_core.functions.params import (
    Params,
    Param,
    ParamInt,
    ParamFloat,
    ParamDatetime,
    ParamJson,
    ParamString,
    ParamBool,
    ParamStringList,
    ParamIntList,
    ParamFloatList,
    ParamDatetimeList,
    ParamBoolList,
)


@pytest.fixture
def parameters():
    params = [
        Param(
            name="param_int",
            type=ParamInt(),
            default=1,
            description="An integer parameter",
        ),
        Param(
            name="param_float",
            type=ParamFloat(),
            default=1.0,
            description="A float parameter",
        ),
        Param(
            name="param_datetime",
            type=ParamDatetime(),
            description="A datetime parameter",
            required=True,
        ),
        Param(
            name="param_json",
            type=ParamJson(),
            default={},
            description="A JSON parameter",
        ),
        Param(
            name="param_string",
            type=ParamString(),
            default="default",
            description="A string parameter",
        ),
        Param(
            name="param_bool",
            type=ParamBool(),
            default=False,
            description="A boolean parameter",
        ),
        Param(
            name="param_string_list",
            type=ParamStringList(),
            default=["a", "b"],
            description="A string list parameter",
        ),
        Param(
            name="param_int_list",
            type=ParamIntList(),
            default=[1, 2],
            description="An int list parameter",
        ),
        Param(
            name="param_float_list",
            type=ParamFloatList(),
            default=[1.0, 2.0],
            description="A float list parameter",
        ),
        Param(
            name="param_datetime_list",
            type=ParamDatetimeList(),
            description="A datetime list parameter",
            required=True,
        ),
        Param(
            name="param_bool_list",
            type=ParamBoolList(),
            default=[True, False],
            description="A bool list parameter",
        ),
    ]
    return Params(*params)


def test_add_param(parameters):
    param = Param(
        name="new_param",
        type=ParamString(),
        default="new",
        description="A new parameter",
    )
    parameters.add_param(param)
    assert "new_param" in parameters.params


def test_parse_cli_arguments(parameters):
    parser = ArgumentParser(prog="test")
    parameters.add_cli_arguments(parser)
    parsed_args = vars(
        parser.parse_args(
            [
                "--param-int",
                "10",
                "--param-float",
                "10.5",
                "--param-datetime",
                "2023-01-01T00:00:00",
                "--param-json",
                '{"key": "value"}',
                "--param-string",
                "test",
                "--param-bool",
                "true",
                "--param-string-list",
                "x,y,z",
                "--param-int-list",
                "3,4,5",
                "--param-float-list",
                "3.5,4.5,5.5",
                "--param-datetime-list",
                "2023-01-01T00:00:00,2023-01-02T00:00:00",
                "--param-bool-list",
                "true,false,true",
            ]
        )
    )
    assert parsed_args["param_int"] == 10
    assert parsed_args["param_float"] == 10.5
    assert parsed_args["param_datetime"] == datetime.fromisoformat(
        "2023-01-01T00:00:00"
    )
    assert parsed_args["param_json"] == {"key": "value"}
    assert parsed_args["param_string"] == "test"
    assert parsed_args["param_bool"] == True
    assert parsed_args["param_string_list"] == ["x", "y", "z"]
    assert parsed_args["param_int_list"] == [3, 4, 5]
    assert parsed_args["param_float_list"] == [3.5, 4.5, 5.5]
    assert parsed_args["param_datetime_list"] == [
        datetime.fromisoformat("2023-01-01T00:00:00"),
        datetime.fromisoformat("2023-01-02T00:00:00"),
    ]
    assert parsed_args["param_bool_list"] == [True, False, True]


def test_parse_dict(parameters):
    data = {
        "param_int": 20,
        "param_float": 20.5,
        "param_datetime": "2023-01-01T00:00:00",
        "param_json": {"key": "value"},
        "param_string": "test",
        "param_bool": True,
        "param_string_list": ["x", "y", "z"],
        "param_int_list": [3, 4, 5],
        "param_float_list": [3.5, 4.5, 5.5],
        "param_datetime_list": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
        "param_bool_list": [True, False, True],
    }
    parsed_data = parameters.parse_dict(data)
    assert parsed_data["param_int"] == 20
    assert parsed_data["param_float"] == 20.5
    assert parsed_data["param_datetime"] == datetime.fromisoformat(
        "2023-01-01T00:00:00"
    )
    assert parsed_data["param_json"] == {"key": "value"}
    assert parsed_data["param_string"] == "test"
    assert parsed_data["param_bool"] == True
    assert parsed_data["param_string_list"] == ["x", "y", "z"]
    assert parsed_data["param_int_list"] == [3, 4, 5]
    assert parsed_data["param_float_list"] == [3.5, 4.5, 5.5]
    assert parsed_data["param_datetime_list"] == [
        datetime.fromisoformat("2023-01-01T00:00:00"),
        datetime.fromisoformat("2023-01-02T00:00:00"),
    ]
    assert parsed_data["param_bool_list"] == [True, False, True]


def test_parse_json(parameters):
    json_input = """
    {
        "PARAM_INT": 30,
        "param_float": 30.5,
        "param_datetime": "2023-01-01T00:00:00",
        "param_json": {"key": "value"},
        "param_string": "test",
        "param_bool": true,
        "param_string_list": ["x", "y", "z"],
        "param_int_list": [3, 4, 5],
        "param_float_list": [3.5, 4.5, 5.5],
        "param_datetime_list": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
        "param_bool_list": [true, false, true]
    }
    """
    parsed_data = parameters.parse_json(json_input)
    assert parsed_data["param_int"] == 30
    assert parsed_data["param_float"] == 30.5
    assert parsed_data["param_datetime"] == datetime.fromisoformat(
        "2023-01-01T00:00:00"
    )
    assert parsed_data["param_json"] == {"key": "value"}
    assert parsed_data["param_string"] == "test"
    assert parsed_data["param_bool"] == True
    assert parsed_data["param_string_list"] == ["x", "y", "z"]
    assert parsed_data["param_int_list"] == [3, 4, 5]
    assert parsed_data["param_float_list"] == [3.5, 4.5, 5.5]
    assert parsed_data["param_datetime_list"] == [
        datetime.fromisoformat("2023-01-01T00:00:00"),
        datetime.fromisoformat("2023-01-02T00:00:00"),
    ]
    assert parsed_data["param_bool_list"] == [True, False, True]


def test_to_dict(parameters):
    params_dict = parameters.to_dict()
    assert "param_int" in params_dict
    assert "param_float" in params_dict
    assert "param_datetime" in params_dict
    assert "param_json" in params_dict
    assert "param_string" in params_dict
    assert "param_bool" in params_dict
    assert "param_string_list" in params_dict
    assert "param_int_list" in params_dict
    assert "param_float_list" in params_dict
    assert "param_datetime_list" in params_dict
    assert "param_bool_list" in params_dict
