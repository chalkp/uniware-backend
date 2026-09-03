import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import (
    DEFAULT_PASSWORD,
    AdminFactory,
    BorrowerProviderFactory,
    ProviderFactory,
    UserFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def borrower(db):
    return UserFactory()


@pytest.fixture
def provider(db):
    return ProviderFactory()


@pytest.fixture
def other_provider(db):
    return ProviderFactory()


@pytest.fixture
def dual_role_user(db):
    return BorrowerProviderFactory()


@pytest.fixture
def admin_user(db):
    return AdminFactory()


@pytest.fixture
def auth_client(db):
    """Factory fixture: auth_client(user) -> APIClient authenticated via the real
    /api/auth/login endpoint, with the CSRF cookie issued by that login carried
    forward as the X-CSRFToken header for subsequent unsafe requests."""

    def _make(user, password=DEFAULT_PASSWORD):
        client = APIClient()
        response = client.post("/api/auth/login", {"email": user.email, "password": password}, format="json")
        assert response.status_code == 200, response.data
        token = client.cookies.get("csrftoken")
        if token:
            client.credentials(HTTP_X_CSRFTOKEN=token.value)
        return client

    return _make
