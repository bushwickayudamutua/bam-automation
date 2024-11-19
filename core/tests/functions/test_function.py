from bam_core.functions.base import Function
from bam_core.functions.params import (
    Params,
    Param,
)


def test_function_run():
    class TestFunction(Function):
        def run(self, params, context):
            return params

    function = TestFunction()
    assert function.run_api({}) == {}


def test_function_run_params_default():
    class TestFunction(Function):
        params = Params(
            Param(
                name="test",
                type="string",
                default="",
                description="Test param",
            )
        )

        def run(self, params, context):
            return params

    function = TestFunction()
    assert function.run_api({}) == {"test": ""}


def test_function_run_raises_param_missing():
    class TestFunction(Function):
        params = Params(
            Param(
                name="test",
                type="string",
                default="",
                description="Test param",
            )
        )

        def run(self, params, context):
            return params

    function = TestFunction()
    try:
        function.run_api({})
    except Exception as e:
        assert str(e) == "Missing required parameter: test"
