import dotenv

dotenv.load_dotenv()

from fastapi.testclient import TestClient
from bam_app.main import app
from bam_app.settings import APIKEY
from unittest.mock import patch

client = TestClient(app)


def test_clean_record_with_valid_input():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=626-420-6969&email=test@test.com"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "test@test.com",
        "email_error": "",
        "phone": "(626) 420-6969",
        "phone_is_invalid": False,
        "phone_is_intl": False,
    }


@patch("bam_app.main.format_address")
def test_clean_record_with_valid_address(mock_format_address):
    mock_format_address.return_value = {
        "cleaned_address": "323 LINDEN ST BROOKLYN NY 11237-5603",
        "bin": "3076151",
        "cleaned_address_accuracy": "Building",
        "plus_code": "87G8M3XP+",
        "lat": 40.703,
        "lng": -73.920,
    }
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=626-420-6969&email=test@test.com&address=323 Linden St&city_state=Brooklyn, NY&zipcode=11237"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "test@test.com",
        "email_error": "",
        "phone": "(626) 420-6969",
        "phone_is_invalid": False,
        "phone_is_intl": False,
        "cleaned_address": "323 LINDEN ST BROOKLYN NY 11237-5603",
        "bin": "3076151",
        "cleaned_address_accuracy": "Building",
        "plus_code": "87G8M3XP+",
        "lat": 40.703,
        "lng": -73.920,
    }


@patch("bam_app.main.format_address")
def test_clean_record_with_invalid_address(mock_format_address):
    mock_format_address.return_value = {
        "cleaned_address": "",
        "bin": "",
        "cleaned_address_accuracy": "No result",
        "plus_code": "",
        "lat": None,
        "lng": None,
    }
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=626-420-6969&email=test@test.com&address=124 Conch St&city_state=Bikini Bottom&zipcode=11111"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "test@test.com",
        "email_error": "",
        "phone": "(626) 420-6969",
        "phone_is_invalid": False,
        "phone_is_intl": False,
        "cleaned_address": "",
        "bin": "",
        "cleaned_address_accuracy": "No result",
        "plus_code": "",
        "lat": None,
        "lng": None,
    }


def test_clean_record_with_valid_intl_number():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=%2b443476669193&email=test@test.com"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "test@test.com",
        "email_error": "",
        "phone": "+44 347 666 9193",
        "phone_is_invalid": False,
        "phone_is_intl": True,
    }


def test_apikey_invalid():
    response = client.get(f"/clean-record?apikey=invalid")
    assert response.status_code == 401


def test_clean_record_with_null_input():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=null&email=null"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "",
        "phone": "",
        "email_error": "No email address provided",
        "phone_is_invalid": True,
        "phone_is_intl": False,
    }


def test_clean_record_with_missing_input():
    response = client.get(f"/clean-record?apikey={APIKEY}&phone=&email=")
    assert response.status_code == 200
    assert response.json() == {
        "email": "",
        "phone": "",
        "email_error": "No email address provided",
        "phone_is_invalid": True,
        "phone_is_intl": False,
    }


def test_clean_record_with_invalid_email():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=&email=invalid"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "invalid",
        "phone": "",
        "email_error": "The email address is not valid. It must have exactly one @-sign.",
        "phone_is_invalid": True,
        "phone_is_intl": False,
    }


def test_clean_record_with_reformatted_email():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=&email=foo @gmail .com"
    )
    assert response.status_code == 200
    assert response.json() == {
        "email": "foo@gmail.com",
        "phone": "",
        "email_error": "",
        "phone_is_invalid": True,
        "phone_is_intl": False,
    }
