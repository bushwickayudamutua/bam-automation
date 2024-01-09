import os
from fastapi import FastAPI
from fastapi import FastAPI, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from bam_core.utils.phone import format_phone_number
from bam_core.utils.email import format_email
from bam_core.utils.geo import format_address


app = FastAPI()

# apikey auth

APIKEY = os.getenv("BAM_APIKEY", "bam")


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
        else:
            response["phone"] = valid_phone
            response["phone_is_invalid"] = False
    else:
        response["phone"] = ""
        response["phone_is_invalid"] = True

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


@app.get("/yo")
def health_check():
    """
    :param email: The phone number to validate
    :return: The formatted email
    """
    return {"status": "ok"}
