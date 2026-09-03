import uuid

import pytest

from apps.equipment.factories import EquipmentFactory

pytestmark = pytest.mark.django_db


def test_us2_3_owner_edits_their_equipment(auth_client, provider):
    equipment = EquipmentFactory(provider=provider, name="Old name")
    client = auth_client(provider)

    response = client.patch(f"/api/equipment/{equipment.id}", {"name": "New name"}, format="json")

    assert response.status_code == 200
    equipment.refresh_from_db()
    assert equipment.name == "New name"


def test_us2_3_rejects_invalid_edit_and_preserves_previous_value(auth_client, provider):
    equipment = EquipmentFactory(provider=provider, name="Old name")
    client = auth_client(provider)

    response = client.patch(f"/api/equipment/{equipment.id}", {"name": ""}, format="json")

    assert response.status_code == 400
    equipment.refresh_from_db()
    assert equipment.name == "Old name"


def test_us2_3_non_owning_provider_cannot_edit_another_providers_equipment(
    auth_client, provider, other_provider
):
    equipment = EquipmentFactory(provider=other_provider, name="Original")
    client = auth_client(provider)

    response = client.patch(f"/api/equipment/{equipment.id}", {"name": "Hijacked"}, format="json")

    assert response.status_code == 404  # Section 2.5: never reveal the object exists
    equipment.refresh_from_db()
    assert equipment.name == "Original"


def test_us2_3_idor_modified_identifier_cannot_mutate_another_providers_equipment(
    auth_client, provider, other_provider
):
    equipment = EquipmentFactory(provider=other_provider, name="Original")
    client = auth_client(provider)

    get_response = client.get(f"/api/equipment/{equipment.id}")
    patch_response = client.patch(f"/api/equipment/{equipment.id}", {"name": "Hijacked"}, format="json")
    missing_response = client.patch(f"/api/equipment/{uuid.uuid4()}", {"name": "Hijacked"}, format="json")

    assert get_response.status_code == 200
    assert patch_response.status_code == missing_response.status_code == 404
    equipment.refresh_from_db()
    assert equipment.name == "Original"


def test_us2_3_editing_nonexistent_equipment_returns_404(auth_client, provider):
    client = auth_client(provider)

    response = client.patch(f"/api/equipment/{uuid.uuid4()}", {"name": "x"}, format="json")

    assert response.status_code == 404
