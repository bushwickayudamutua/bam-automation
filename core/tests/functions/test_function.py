from bam_core.functions.base import Function


class TestFunction(Function):
    test: str = ""

    def run(self):
        return {"test": self.test}


def test_function_run_params_default():
    function = TestFunction()
    assert function.run() == {"test": ""}


def test_function_run_params_non_default():
    test = "Hello, Bushwick!"
    function = TestFunction(test=test)
    assert function.run() == {"test": test}
