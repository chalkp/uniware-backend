import pytest

from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus

pytestmark = pytest.mark.django_db


def test_us2_2_provider_sees_only_their_own_equipment(auth_client, provider, other_provider):
    mine = EquipmentFactory(provider=provider)
    EquipmentFactory(provider=other_provider)
    client = auth_client(provider)

    response = client.get("/api/provider/equipment")

    assert response.status_code == 200
    ids = {item["id"] for item in response.data["results"]}
    assert ids == {str(mine.id)}


def test_us2_2_includes_archived_and_disabled_equipment_owned_by_the_provider(auth_client, provider):
    EquipmentFactory(provider=provider, status=EquipmentStatus.ARCHIVED)
    EquipmentFactory(provider=provider, status=EquipmentStatus.DISABLED)
    client = auth_client(provider)

    response = client.get("/api/provider/equipment")

    assert response.status_code == 200
    assert len(response.data["results"]) == 2


def test_us2_2_denies_borrower_without_provider_capability(auth_client, borrower):
    response = auth_client(borrower).get("/api/provider/equipment")

    assert response.status_code == 403


def test_us2_2_denies_anonymous_access(api_client):
    response = api_client.get("/api/provider/equipment")

    assert response.status_code == 401
