import pytest

pytestmark = pytest.mark.django_db


def test_profile_requires_authentication(api_client):
    response = api_client.get("/api/profile")

    assert response.status_code == 401


def test_profile_returns_the_authenticated_users_data(auth_client, borrower, other_provider):
    response = auth_client(borrower).get("/api/profile")

    assert response.status_code == 200
    assert response.data["id"] == str(borrower.id)
    assert response.data["email"] == borrower.email
    assert response.data["first_name"] == borrower.first_name
    assert "password" not in response.data
    assert response.data["email"] != other_provider.email


def test_profile_patch_updates_editable_fields(auth_client, borrower):
    response = auth_client(borrower).patch(
        "/api/profile",
        {"first_name": "Somchai", "last_name": "Srisawat", "department": "Engineering"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["first_name"] == "Somchai"
    assert response.data["last_name"] == "Srisawat"
    assert response.data["department"] == "Engineering"
    borrower.refresh_from_db()
    assert borrower.first_name == "Somchai"
    assert borrower.department == "Engineering"


def test_profile_patch_rejects_invalid_name_without_changing_profile(auth_client, borrower):
    original_name = borrower.first_name
    response = auth_client(borrower).patch("/api/profile", {"first_name": "Invalid123"}, format="json")

    assert response.status_code == 400
    borrower.refresh_from_db()
    assert borrower.first_name == original_name


@pytest.mark.parametrize("restricted_field,value", [("email", "other@chula.ac.th"), ("is_admin", True)])
def test_profile_patch_rejects_restricted_fields(auth_client, borrower, restricted_field, value):
    original_email = borrower.email
    original_admin = borrower.is_admin
    response = auth_client(borrower).patch("/api/profile", {restricted_field: value}, format="json")

    assert response.status_code == 400
    borrower.refresh_from_db()
    assert borrower.email == original_email
    assert borrower.is_admin == original_admin
