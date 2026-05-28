from pathlib import Path
import traceback as tb
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bam_core.functions.registry import (
    init_function,
    list_function_module_names,
    resolve_function_class,
)
from bam_core.utils.phone import (
    format_phone_number,
    is_international_phone_number,
)
from bam_core.utils.email import format_email
from bam_core.utils.geo import format_address
from bam_app.settings import APIKEY

_HERE = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=_HERE / "static"), name="static")
templates = Jinja2Templates(directory=_HERE / "templates")



def _get_function(function_name: str):
    """
    Resolve and instantiate a bam_core Function, translating registry errors
    to the appropriate HTTP status codes at the API boundary.
    """
    try:
        return init_function(function_name)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# apikey authentication
def check_api_key(apikey: str):
    if apikey != APIKEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key"
        )


@app.get("/clean-record")
def clean_record(
    apikey: str,
    phone: str = None,
    email: str = None,
    dns_check: bool = False,
    address: str = None,
    city_state: str = "",
    zip_code: str = "",
):
    """
    :param phone_number: The phone number to validate
    :return: The formatted phone number
    """
    check_api_key(apikey)
    response = {}

    # validate phone number
    if phone and phone != "null":
        valid_phone = format_phone_number(phone)
        if not valid_phone:
            response["phone"] = phone
            response["phone_is_invalid"] = True
            response["phone_is_intl"] = False
        else:
            response["phone"] = valid_phone
            response["phone_is_invalid"] = False
            response["phone_is_intl"] = is_international_phone_number(phone)
    else:
        response["phone"] = ""
        response["phone_is_invalid"] = True
        response["phone_is_intl"] = False

    # validate email address
    if email and email != "null":
        email_info = format_email(email, dns_check=dns_check)
        response["email"] = email_info["email"]
        response["email_error"] = email_info["error"] or ""
    else:
        response["email"] = ""
        response["email_error"] = "No email address provided"

    # validate mailing address
    if address:
        address_response = format_address(
            address=address, city_state=city_state, zipcode=zip_code
        )
        response.update(address_response)
    return response


@app.post("/functions/{function_name}")
def run_function(
    function_name: str,
    apikey: str,
    params: Optional[Dict[str, Any]] = None,
):
    """
    Run a bam_core function by module name using JSON params.
    Returns both the function response and collected logs.
    """
    check_api_key(apikey)
    fn = _get_function(function_name)
    payload = params or {}

    try:
        response = fn.run_api(payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "error": f"{type(e).__name__}: {e}",
                "logs": fn.log_lines,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": f"{type(e).__name__}: {e}\n\n{tb.format_exc()}",
                "logs": fn.log_lines,
            },
        )

    return {
        "function_name": function_name,
        "response": response,
        "logs": fn.log_lines,
    }


@app.options("/functions/{function_name}")
def function_schema(function_name: str, apikey: str):
    """
    Return function parameter metadata generated from the shared Params interface.
    """
    check_api_key(apikey)
    fn = _get_function(function_name)
    return {
        "function_name": function_name,
        "description": (fn.__class__.__doc__ or "").strip(),
        "params": fn.params.to_dict(),
    }


@app.get("/functions")
def list_functions(apikey: str):
    """
    Return all available function names and their parameter schema.
    """
    check_api_key(apikey)
    functions = []
    load_errors = []

    for function_name in list_function_module_names():
        try:
            fn = init_function(function_name)
            functions.append(
                {
                    "function_name": function_name,
                    "description": (fn.__class__.__doc__ or "").strip(),
                    "params": fn.params.to_dict(),
                }
            )
        except (ValueError, RuntimeError) as e:
            load_errors.append(
                {
                    "function_name": function_name,
                    "detail": str(e),
                }
            )

    return {
        "functions": functions,
        "load_errors": load_errors,
    }


@app.get("/")
def functions_ui(request: Request):
    """
    Serve the UI for running and inspecting bam_core functions.
    """
    return templates.TemplateResponse(
        request=request,
        name="functions_ui.html",
        context={},
    )


@app.get("/yo")
def health_check():
    """
    :param email: The phone number to validate
    :return: The formatted email
    """
    return {"status": "ok"}
