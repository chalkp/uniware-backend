import pytest

from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus

pytestmark = pytest.mark.django_db


def test_us3_1_shows_active_visible_equipment_with_summary_info(auth_client, borrower):
    visible = EquipmentFactory(status=EquipmentStatus.AVAILABLE, name="Visible Item")
    client = auth_client(borrower)

    response = client.get("/api/equipment")

    assert response.status_code == 200
    item = next(i for i in response.data["results"] if i["id"] == str(visible.id))
    assert item["name"] == "Visible Item"
    assert "category" in item and "location" in item and "status" in item


def test_us3_1_excludes_archived_and_disabled_equipment(auth_client, borrower):
    archived = EquipmentFactory(status=EquipmentStatus.ARCHIVED)
    disabled = EquipmentFactory(status=EquipmentStatus.DISABLED)
    client = auth_client(borrower)

    response = client.get("/api/equipment")

    ids = [item["id"] for item in response.data["results"]]
    assert str(archived.id) not in ids
    assert str(disabled.id) not in ids


def test_us3_1_denies_anonymous_browsing(api_client):
    response = api_client.get("/api/equipment")

    assert response.status_code == 401


def test_us3_2_search_matches_partial_equipment_name_case_insensitively(auth_client, borrower):
    matching = EquipmentFactory(name="Nikon Camera")
    EquipmentFactory(name="Canon Camera")
    client = auth_client(borrower)

    response = client.get("/api/equipment", {"search": "nikon"})

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(matching.id)]


def test_us3_2_search_matches_model_and_excludes_hidden_equipment(auth_client, borrower):
    matching = EquipmentFactory(name="Camera", model="Nikon D850")
    EquipmentFactory(name="Hidden Camera", model="Nikon D850", status=EquipmentStatus.ARCHIVED)
    EquipmentFactory(name="Disabled Camera", model="Nikon D850", status=EquipmentStatus.DISABLED)
    client = auth_client(borrower)

    response = client.get("/api/equipment", {"search": "d850"})

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(matching.id)]
