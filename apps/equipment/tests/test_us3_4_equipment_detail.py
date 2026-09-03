import uuid

import pytest

from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus

pytestmark = pytest.mark.django_db


def test_us3_4_shows_detail_for_visible_equipment(auth_client, borrower):
    equipment = EquipmentFactory(name="Detail Item", status=EquipmentStatus.AVAILABLE)
    client = auth_client(borrower)

    response = client.get(f"/api/equipment/{equipment.id}")

    assert response.status_code == 200
    assert response.data["name"] == "Detail Item"
    assert response.data["category"]["id"] == str(equipment.category_id)
    assert response.data["location"]["id"] == str(equipment.location_id)
    assert response.data["status"] == EquipmentStatus.AVAILABLE


def test_us3_4_returns_not_found_for_nonexistent_equipment(auth_client, borrower):
    client = auth_client(borrower)

    response = client.get(f"/api/equipment/{uuid.uuid4()}")

    assert response.status_code == 404


def test_us3_4_returns_not_found_for_archived_equipment_without_leaking_it(auth_client, borrower):
    equipment = EquipmentFactory(status=EquipmentStatus.ARCHIVED)
    client = auth_client(borrower)

    response = client.get(f"/api/equipment/{equipment.id}")

    assert response.status_code == 404
