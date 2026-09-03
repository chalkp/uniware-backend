import pytest

from apps.equipment.factories import CategoryFactory, EquipmentFactory, LocationFactory

pytestmark = pytest.mark.django_db


def test_role_matrix_create_equipment(api_client, auth_client, borrower, provider, admin_user):
    category = CategoryFactory()
    location = LocationFactory()
    payload = {
        "asset_id": "RM-0000",
        "name": "Role Matrix Item",
        "category_id": str(category.id),
        "location_id": str(location.id),
    }

    assert api_client.post("/api/equipment", payload, format="json").status_code == 401

    assert (
        auth_client(borrower)
        .post("/api/equipment", {**payload, "asset_id": "RM-0001"}, format="json")
        .status_code
        == 403
    )

    # Admin without provider capability still cannot create equipment — admin and
    # provider are independent capabilities (docs/DECISIONS.md).
    assert (
        auth_client(admin_user)
        .post("/api/equipment", {**payload, "asset_id": "RM-0002"}, format="json")
        .status_code
        == 403
    )

    assert (
        auth_client(provider)
        .post("/api/equipment", {**payload, "asset_id": "RM-0003"}, format="json")
        .status_code
        == 201
    )


def test_role_matrix_edit_equipment(api_client, auth_client, borrower, provider, other_provider, admin_user):
    equipment = EquipmentFactory(provider=provider)
    url = f"/api/equipment/{equipment.id}"

    assert api_client.patch(url, {"name": "x"}, format="json").status_code == 401
    assert auth_client(borrower).patch(url, {"name": "x"}, format="json").status_code == 403
    assert auth_client(admin_user).patch(url, {"name": "x"}, format="json").status_code == 403
    assert auth_client(other_provider).patch(url, {"name": "x"}, format="json").status_code == 404
    assert auth_client(provider).patch(url, {"name": "Renamed"}, format="json").status_code == 200


def test_role_matrix_view_my_equipment(api_client, auth_client, borrower, provider, admin_user):
    EquipmentFactory(provider=provider)

    assert api_client.get("/api/provider/equipment").status_code == 401
    assert auth_client(borrower).get("/api/provider/equipment").status_code == 403
    assert auth_client(admin_user).get("/api/provider/equipment").status_code == 403
    assert auth_client(provider).get("/api/provider/equipment").status_code == 200
