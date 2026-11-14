import pytest

from apps.accounts.factories import DEFAULT_PASSWORD
from apps.accounts.models import AccountStatus

pytestmark = pytest.mark.django_db


def status_url(user):
    return f"/api/auth/users/{user.id}/status"


def test_admin_can_suspend_and_reactivate_and_session_is_revoked(auth_client, api_client, admin_user, borrower):
    borrower_session = auth_client(borrower)
    admin_session = auth_client(admin_user)
    assert borrower_session.get("/api/auth/me").status_code == 200

    suspended = admin_session.patch(status_url(borrower), {"account_status": "SUSPENDED"}, format="json")
    assert suspended.status_code == 200
    assert suspended.data["account_status"] == AccountStatus.SUSPENDED
    borrower.refresh_from_db()
    assert borrower.is_active is False
    assert borrower.account_status == AccountStatus.SUSPENDED
    assert borrower_session.get("/api/auth/me").status_code == 401
    assert api_client.post(
        "/api/auth/login", {"email": borrower.email, "password": DEFAULT_PASSWORD}, format="json"
    ).status_code == 401

    active = admin_session.patch(status_url(borrower), {"account_status": "ACTIVE"}, format="json")
    assert active.status_code == 200
    borrower.refresh_from_db()
    assert borrower.is_active is True
    assert borrower.account_status == AccountStatus.ACTIVE
    # An old session must stay invalid even after the account is reactivated.
    assert borrower_session.get("/api/auth/me").status_code == 401
    assert api_client.post(
        "/api/auth/login", {"email": borrower.email, "password": DEFAULT_PASSWORD}, format="json"
    ).status_code == 200


def test_only_admin_can_update_status(auth_client, api_client, borrower, provider):
    assert api_client.patch(status_url(borrower), {"account_status": "SUSPENDED"}, format="json").status_code == 401
    assert auth_client(provider).patch(
        status_url(borrower), {"account_status": "SUSPENDED"}, format="json"
    ).status_code == 403
    borrower.refresh_from_db()
    assert borrower.account_status == AccountStatus.ACTIVE


def test_admin_cannot_suspend_self(auth_client, admin_user):
    response = auth_client(admin_user).patch(
        status_url(admin_user), {"account_status": "SUSPENDED"}, format="json"
    )
    assert response.status_code == 400
    admin_user.refresh_from_db()
    assert admin_user.is_active is True
    assert admin_user.account_status == AccountStatus.ACTIVE


@pytest.mark.parametrize("payload", [{"account_status": "UNKNOWN"}, {}, {"account_status": "SUSPENDED", "is_admin": True}])
def test_status_change_rejects_invalid_payload(auth_client, admin_user, borrower, payload):
    response = auth_client(admin_user).patch(status_url(borrower), payload, format="json")
    assert response.status_code == 400
    borrower.refresh_from_db()
    assert borrower.account_status == AccountStatus.ACTIVE


def test_role_management_does_not_change_account_status(auth_client, admin_user, borrower):
    client = auth_client(admin_user)
    assert client.patch(status_url(borrower), {"account_status": "SUSPENDED"}, format="json").status_code == 200
    response = client.patch(f"/api/auth/users/{borrower.id}/roles", {"is_provider": True}, format="json")
    assert response.status_code == 200
    borrower.refresh_from_db()
    assert borrower.is_provider is True
    assert borrower.account_status == AccountStatus.SUSPENDED
    assert borrower.is_active is False
