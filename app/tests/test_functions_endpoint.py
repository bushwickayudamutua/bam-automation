from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from bam_app.main import app
from bam_app.settings import APIKEY

client = TestClient(app)


class DummyParams:
    def to_dict(self):
        return {
            "dry_run": {
                "name": "dry_run",
                "type": "bool",
                "default": True,
                "description": "If true, no writes happen",
                "required": False,
            }
        }


class DummyFunction:
    def __init__(self):
        self.params = DummyParams()
        self.log_lines = []

    def run_api(self, params):
        self.log_lines.append(
            {
                "level": "info",
                "message": "ran dummy function",
                "time": "2026-01-01T00:00:00Z",
            }
        )
        return {"echo": params}


class ErrorFunction(DummyFunction):
    def run_api(self, params):
        self.log_lines.append(
            {
                "level": "error",
                "message": "bad input",
                "time": "2026-01-01T00:00:00Z",
            }
        )
        raise ValueError("Missing required parameter: request_value")


@patch("bam_app.main._get_function", return_value=DummyFunction())
def test_post_function_returns_response_and_logs(_mock_get_function):
    response = client.post(
        f"/functions/timeout_eg_requests?apikey={APIKEY}",
        json={"dry_run": True},
    )

    assert response.status_code == 200
    assert response.json() == {
        "function_name": "timeout_eg_requests",
        "response": {"echo": {"dry_run": True}},
        "logs": [
            {
                "level": "info",
                "message": "ran dummy function",
                "time": "2026-01-01T00:00:00Z",
            }
        ],
    }


@patch("bam_app.main._get_function", return_value=DummyFunction())
def test_options_function_returns_param_schema(_mock_get_function):
    response = client.options(
        f"/functions/timeout_eg_requests?apikey={APIKEY}"
    )

    assert response.status_code == 200
    assert response.json() == {
        "function_name": "timeout_eg_requests",
        "description": "",
        "params": {
            "dry_run": {
                "name": "dry_run",
                "type": "bool",
                "default": True,
                "description": "If true, no writes happen",
                "required": False,
            }
        },
    }


@patch("bam_app.main._get_function", return_value=ErrorFunction())
def test_post_function_validation_error_returns_logs(_mock_get_function):
    response = client.post(
        f"/functions/timeout_eg_requests?apikey={APIKEY}",
        json={"dry_run": True},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "error": "Missing required parameter: request_value",
            "logs": [
                {
                    "level": "error",
                    "message": "bad input",
                    "time": "2026-01-01T00:00:00Z",
                }
            ],
        }
    }


@patch(
    "bam_app.main._get_function",
    side_effect=HTTPException(status_code=404, detail="Function not found"),
)
def test_post_function_not_found(_mock_get_function):
    response = client.post(
        f"/functions/not_a_real_function?apikey={APIKEY}",
        json={},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Function not found"}


@patch("bam_app.main.list_function_module_names", return_value=["foo", "bar"])
@patch("bam_app.main.init_function")
def test_get_functions_returns_all_schemas(
    mock_init_function, _mock_list_function_module_names
):
    mock_init_function.side_effect = [DummyFunction(), DummyFunction()]

    response = client.get(f"/functions?apikey={APIKEY}")

    assert response.status_code == 200
    assert response.json() == {
        "functions": [
            {
                "function_name": "foo",
                "description": "",
                "params": {
                    "dry_run": {
                        "name": "dry_run",
                        "type": "bool",
                        "default": True,
                        "description": "If true, no writes happen",
                        "required": False,
                    }
                },
            },
            {
                "function_name": "bar",
                "description": "",
                "params": {
                    "dry_run": {
                        "name": "dry_run",
                        "type": "bool",
                        "default": True,
                        "description": "If true, no writes happen",
                        "required": False,
                    }
                },
            },
        ],
        "load_errors": [],
    }


@patch("bam_app.main.list_function_module_names", return_value=["ok_fn", "bad_fn"])
@patch("bam_app.main.init_function")
def test_get_functions_includes_load_errors(
    mock_init_function, _mock_list_function_module_names
):
    mock_init_function.side_effect = [
        DummyFunction(),
        RuntimeError("boom"),
    ]

    response = client.get(f"/functions?apikey={APIKEY}")

    assert response.status_code == 200
    assert response.json() == {
        "functions": [
            {
                "function_name": "ok_fn",
                "description": "",
                "params": {
                    "dry_run": {
                        "name": "dry_run",
                        "type": "bool",
                        "default": True,
                        "description": "If true, no writes happen",
                        "required": False,
                    }
                },
            }
        ],
        "load_errors": [
            {
                "function_name": "bad_fn",
                "detail": "boom",
            }
        ],
    }


def test_functions_ui_is_publicly_accessible():
    response = client.get("/")
    assert response.status_code == 200
    assert "Functions Runner" in response.text


def test_functions_ui_returns_html_for_valid_apikey():
    response = client.get(f"/?apikey={APIKEY}")
    assert response.status_code == 200
    assert "Functions Runner" in response.text
