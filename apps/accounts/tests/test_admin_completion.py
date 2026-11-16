import pytest

from apps.accounts.factories import UserFactory
from apps.equipment.factories import EquipmentFactory
from apps.requests.tests.test_handover import approved

pytestmark = pytest.mark.django_db


def test_user_search_pagination_and_privacy(auth_client, admin_user, borrower):
    UserFactory.create_batch(22)
    match = UserFactory(first_name="Searchable", last_name="Person")
    client = auth_client(admin_user)
    page = client.get("/api/auth/users")
    assert len(page.data["results"]) == 20
    assert page.data["next"]
    for query in ["SEARCHABLE person", match.email]:
        response = client.get("/api/auth/users", {"search": query})
        assert response.data["count"] == 1
        assert response.data["results"][0]["id"] == str(match.pk)
        assert "password" not in response.data["results"][0]
    assert client.get("/api/auth/users?search=nomatch").data["count"] == 0
    assert auth_client(borrower).get("/api/auth/users").status_code == 403


def test_role_validation_and_existing_session(auth_client, admin_user, borrower):
    client = auth_client(admin_user)
    session = auth_client(borrower)
    url = f"/api/auth/users/{borrower.pk}/roles"
    assert client.patch(url, {"is_superuser": True}, format="json").status_code == 400
    assert client.patch(url, {"is_provider": "yes"}, format="json").status_code == 400
    assert session.get("/api/provider/requests").status_code == 403
    assert client.patch(url, {"is_provider": True}, format="json").status_code == 200
    assert session.get("/api/provider/requests").status_code == 200
    assert client.patch(url, {"is_provider": False}, format="json").status_code == 200
    assert session.get("/api/provider/requests").status_code == 403


def test_disabled_listing_hidden_before_pagination_and_history_retained(
    auth_client, admin_user, borrower, provider
):
    record = approved(borrower, provider)
    item = record.equipment
    admin = auth_client(admin_user)
    url = f"/api/admin/equipment/{item.pk}/disable"
    assert auth_client(provider).post(url, {"reason": "No"}, format="json").status_code == 403
    assert admin.post(url, {"reason": " "}, format="json").status_code == 400
    assert admin.post(url, {"reason": "Retired listing"}, format="json").status_code == 200
    item.refresh_from_db()
    stamp = item.disabled_at
    assert item.status == "AVAILABLE"
    assert admin.post(url, {"reason": "Another"}, format="json").status_code == 200
    item.refresh_from_db()
    assert item.disabled_at == stamp
    assert item.disabled_reason == "Retired listing"
    EquipmentFactory.create_batch(21, admin_suspended=True)
    visible = EquipmentFactory()
    client = auth_client(borrower)
    page = client.get("/api/equipment")
    assert page.data["count"] == 1
    assert page.data["results"][0]["id"] == str(visible.pk)
    assert client.get(f"/api/equipment/{item.pk}").status_code == 404
    assert client.get("/api/equipment", {"search": item.asset_id}).data["count"] == 0
    assert client.get(f"/api/requests/borrow-requests/{record.pk}/").status_code == 200
    assert admin.get("/api/admin/equipment").data["count"] == 23
    assert (
        auth_client(provider)
        .post(f"/api/provider/requests/{record.pk}/checkout", {}, format="json")
        .status_code
        == 409
    )
