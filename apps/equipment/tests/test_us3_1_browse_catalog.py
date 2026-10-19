import pytest

from apps.equipment.factories import CategoryFactory, EquipmentFactory, LocationFactory
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


# US3-2: Equipment Search Tests
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


# US3-3: Equipment Catalog Filtering Tests
def test_us3_3_combines_category_and_location_filters_with_and(auth_client, borrower):
    category = CategoryFactory()
    location = LocationFactory()
    matching = EquipmentFactory(category=category, location=location)
    EquipmentFactory(category=category)
    EquipmentFactory(location=location)
    client = auth_client(borrower)

    response = client.get("/api/equipment", {"category": str(category.id), "location": str(location.id)})

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(matching.id)]


def test_us3_3_filters_available_and_unavailable_catalog_items(auth_client, borrower):
    available = EquipmentFactory(status=EquipmentStatus.AVAILABLE)
    unavailable = [
        EquipmentFactory(status=EquipmentStatus.RESERVED),
        EquipmentFactory(status=EquipmentStatus.CHECKED_OUT),
        EquipmentFactory(status=EquipmentStatus.MAINTENANCE),
    ]
    EquipmentFactory(status=EquipmentStatus.ARCHIVED)
    client = auth_client(borrower)

    available_response = client.get("/api/equipment", {"availability": "available"})
    unavailable_response = client.get("/api/equipment", {"availability": "unavailable"})

    assert available_response.status_code == 200
    assert [item["id"] for item in available_response.data["results"]] == [str(available.id)]
    assert unavailable_response.status_code == 200
    assert {item["id"] for item in unavailable_response.data["results"]} == {
        str(item.id) for item in unavailable
    }


def test_us3_3_returns_empty_results_when_a_valid_filter_has_no_matches(auth_client, borrower):
    category = CategoryFactory()

    response = auth_client(borrower).get("/api/equipment", {"category": str(category.id)})

    assert response.status_code == 200
    assert response.data["count"] == 0
    assert response.data["results"] == []


@pytest.mark.parametrize(
    ("filters", "field"),
    [({"category": "not-a-uuid"}, "category"), ({"availability": "sometimes"}, "availability")],
)
def test_us3_3_rejects_invalid_filter_values(auth_client, borrower, filters, field):
    response = auth_client(borrower).get("/api/equipment", filters)

    assert response.status_code == 400
    assert response.data["error"]["code"] == "VALIDATION_ERROR"
    assert field in response.data["error"]["details"]
