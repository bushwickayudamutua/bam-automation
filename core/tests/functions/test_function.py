from pydantic import BaseModel
from bam_core.functions.base import Function


def test_function_run():
    class TestParams(BaseModel): pass

    class TestFunction(Function[TestParams]):
        def run(self, params):
            return params

    function = TestFunction()
    assert function.run(TestParams()) == {}


def test_function_run_params_default():
    class TestParams(BaseModel):
        test: str = ""

    class TestFunction(Function[TestParams]):
        def run(self, params):
            return params

    function = TestFunction()
    assert function.run(TestParams()) == {"test": ""}


def test_function_run_raises_param_missing():
    class TestParams(BaseModel):
        test: str = ""

    class TestFunction(Function[TestParams]):
        def run(self, params):
            return params

    function = TestFunction()
    try:
        function.run(TestParams())
    except Exception as e:
        assert str(e) == "Missing required parameter: test"
