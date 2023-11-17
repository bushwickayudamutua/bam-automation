from fastapi.testclient import TestClient
from bam_app.main import app, APIKEY

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
    }


def test_clean_record_with_missing_input():
    response = client.get(f"/clean-record?apikey={APIKEY}&phone=&email=")
    assert response.status_code == 200
    assert response.json() == {
        "email": "",
        "phone": "",
        "email_error": "No email address provided",
        "phone_is_invalid": True,
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
    }


def test_clean_record_with_reformatted_email():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=&email=foo @gmail .com"
    )
    assert response.status_code == 200
    print(response.json())
    assert response.json() == {
        "email": "foo@gmail.com",
        "phone": "",
        "email_error": "",
        "phone_is_invalid": True,
    }


def test_clean_record_with_reformatted_email():
    response = client.get(
        f"/clean-record?apikey={APIKEY}&phone=&email=foo @gmail .com"
    )
    assert response.status_code == 200
    print(response.json())
    assert response.json() == {
        "email": "foo@gmail.com",
        "phone": "",
        "email_error": "",
        "phone_is_invalid": True,
    }
