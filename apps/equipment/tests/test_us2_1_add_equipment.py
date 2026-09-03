import pytest

from apps.equipment.factories import CategoryFactory, LocationFactory
from apps.equipment.models import Equipment

pytestmark = pytest.mark.django_db


def _payload(category, location, **overrides):
    payload = {
        "asset_id": "AST-0001",
        "name": "Oscilloscope",
        "model": "Tektronix TBS2000",
        "description": "100MHz 4-channel oscilloscope",
        "category_id": str(category.id),
        "location_id": str(location.id),
    }
    payload.update(overrides)
    return payload


def test_us2_1_provider_creates_equipment_with_valid_unique_asset_id(auth_client, provider):
    category = CategoryFactory()
    location = LocationFactory()
    client = auth_client(provider)

    response = client.post("/api/equipment", _payload(category, location), format="json")

    assert response.status_code == 201
    equipment = Equipment.objects.get(asset_id="AST-0001")
    assert equipment.provider_id == provider.id
    assert equipment.category_id == category.id


def test_us2_1_client_supplied_provider_is_ignored(auth_client, provider, other_provider):
    category = CategoryFactory()
    location = LocationFactory()
    client = auth_client(provider)

    response = client.post(
        "/api/equipment",
        _payload(category, location, asset_id="AST-0099", provider=str(other_provider.id)),
        format="json",
    )

    assert response.status_code == 201
    equipment = Equipment.objects.get(asset_id="AST-0099")
    assert equipment.provider_id == provider.id


def test_us2_1_rejects_duplicate_asset_id(auth_client, provider):
    category = CategoryFactory()
    location = LocationFactory()
    client = auth_client(provider)
    client.post("/api/equipment", _payload(category, location), format="json")

    response = client.post("/api/equipment", _payload(category, location, name="Second unit"), format="json")

    assert response.status_code == 400
    assert Equipment.objects.filter(asset_id="AST-0001").count() == 1


def test_us2_1_rejects_incomplete_equipment_info(auth_client, provider):
    category = CategoryFactory()
    location = LocationFactory()
    client = auth_client(provider)
    payload = _payload(category, location)
    del payload["name"]

    response = client.post("/api/equipment", payload, format="json")

    assert response.status_code == 400
    assert not Equipment.objects.filter(asset_id="AST-0001").exists()


def test_us2_1_rejects_borrower_without_provider_capability(auth_client, borrower):
    category = CategoryFactory()
    location = LocationFactory()
    client = auth_client(borrower)

    response = client.post("/api/equipment", _payload(category, location), format="json")

    assert response.status_code == 403
    assert not Equipment.objects.exists()


def test_us2_1_rejects_anonymous_request(api_client):
    category = CategoryFactory()
    location = LocationFactory()

    response = api_client.post("/api/equipment", _payload(category, location), format="json")

    assert response.status_code == 401
    assert not Equipment.objects.exists()
