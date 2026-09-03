import pytest

from apps.accounts.factories import DEFAULT_PASSWORD

pytestmark = pytest.mark.django_db


def test_us1_3_logout_invalidates_session_server_side(api_client, borrower):
    login_response = api_client.post(
        "/api/auth/login", {"email": borrower.email, "password": DEFAULT_PASSWORD}, format="json"
    )
    assert login_response.status_code == 200
    api_client.credentials(HTTP_X_CSRFTOKEN=api_client.cookies["csrftoken"].value)

    logout_response = api_client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    me_response = api_client.get("/api/auth/me")
    assert me_response.status_code == 401


def test_us1_3_protected_page_denied_without_active_session(api_client):
    response = api_client.get("/api/auth/me")

    assert response.status_code == 401
