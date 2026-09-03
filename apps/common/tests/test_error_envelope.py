import pytest

pytestmark = pytest.mark.django_db


def test_error_envelope_shape_on_permission_denied(auth_client, borrower):
    response = auth_client(borrower).get("/api/provider/equipment")

    assert response.status_code == 403
    body = response.data
    assert set(body.keys()) == {"error"}
    assert set(body["error"].keys()) == {"code", "message", "details"}
    assert body["error"]["code"] == "PERMISSION_DENIED"


def test_error_envelope_shape_on_authentication_required(api_client):
    response = api_client.get("/api/provider/equipment")

    assert response.status_code == 401
    assert response.data["error"]["code"] == "AUTHENTICATION_REQUIRED"
