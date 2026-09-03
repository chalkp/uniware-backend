import pytest

from apps.accounts.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db


def test_us1_2_correct_credentials_create_session(api_client, borrower):
    response = api_client.post(
        "/api/auth/login", {"email": borrower.email, "password": DEFAULT_PASSWORD}, format="json"
    )

    assert response.status_code == 200
    assert response.data["email"] == borrower.email
    assert "sessionid" in response.cookies

    me_response = api_client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.data["email"] == borrower.email


def test_us1_2_rejects_incorrect_password(api_client, borrower):
    response = api_client.post(
        "/api/auth/login", {"email": borrower.email, "password": "WrongPassword123!"}, format="json"
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_CREDENTIALS"

    me_response = api_client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_us1_2_rejects_unknown_email(api_client):
    response = api_client.post(
        "/api/auth/login", {"email": "nobody@chula.ac.th", "password": "WhoKnows123!"}, format="json"
    )

    assert response.status_code == 401
    assert response.data["error"]["code"] == "INVALID_CREDENTIALS"
