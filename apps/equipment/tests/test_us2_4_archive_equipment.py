import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import Equipment, EquipmentStatus
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def make_request(equipment, borrower, status):
    return BorrowRequest.objects.create(
        equipment=equipment,
        borrower=borrower,
        pickup_date=timezone.localdate(),
        due_date=timezone.localdate() + timedelta(days=1),
        purpose="Research",
        status=status,
    )


def test_archive_retains_equipment_history_and_timestamp(auth_client, provider, borrower):
    equipment = EquipmentFactory(provider=provider)
    history = [
        make_request(equipment, borrower, status)
        for status in ("PENDING", "REJECTED", "CANCELLED", "COMPLETED")
    ]
    asset_id = equipment.asset_id
    client = auth_client(provider)
    url = f"/api/equipment/{equipment.id}/archive"

    response = client.post(url)

    assert response.status_code == 200
    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.ARCHIVED
    assert equipment.archived_at is not None
    assert equipment.asset_id == asset_id
    assert response.data["status"] == "ARCHIVED"
    archived_at = equipment.archived_at
    for record in history:
        old_status = record.status
        record.refresh_from_db()
        assert record.status == old_status
        assert record.equipment_id == equipment.id
    assert client.post(url).status_code == 200
    equipment.refresh_from_db()
    assert equipment.archived_at == archived_at
    inventory = client.get("/api/provider/equipment")
    assert inventory.data["results"][0]["status"] == "ARCHIVED"

    borrower_client = auth_client(borrower)
    for record in history:
        response = borrower_client.get(reverse("borrow-request-detail", args=[record.id]))
        assert response.status_code == 200
        assert response.data["equipment"]["asset_id"] == asset_id


def test_archive_wrong_owner_matches_missing_equipment(auth_client, provider, other_provider):
    equipment = EquipmentFactory(provider=other_provider)
    client = auth_client(provider)
    assert client.post(f"/api/equipment/{equipment.id}/archive").status_code == 404
    assert client.post(f"/api/equipment/{uuid.uuid4()}/archive").status_code == 404
    equipment.refresh_from_db()
    assert equipment.status == EquipmentStatus.AVAILABLE
    assert equipment.archived_at is None


def test_archive_requires_provider(auth_client, api_client, borrower):
    equipment = EquipmentFactory()
    url = f"/api/equipment/{equipment.id}/archive"
    assert api_client.post(url).status_code == 401
    assert auth_client(borrower).post(url).status_code == 403


@pytest.mark.parametrize("equipment_status", ["RESERVED", "CHECKED_OUT"])
def test_archive_blocks_active_equipment_status(auth_client, provider, equipment_status):
    equipment = EquipmentFactory(provider=provider, status=equipment_status)
    response = auth_client(provider).post(f"/api/equipment/{equipment.id}/archive")
    assert response.status_code == 409
    assert response.data["error"]["code"] == "BOOKING_CONFLICT"
    equipment.refresh_from_db()
    assert equipment.status == equipment_status
    assert equipment.archived_at is None


@pytest.mark.parametrize("request_status", ["APPROVED", "CHECKED_OUT"])
def test_archive_blocks_active_requests_even_when_equipment_available(
    auth_client, provider, borrower, request_status
):
    equipment = EquipmentFactory(provider=provider)
    record = make_request(equipment, borrower, request_status)
    response = auth_client(provider).post(f"/api/equipment/{equipment.id}/archive")
    assert response.status_code == 409
    equipment.refresh_from_db()
    record.refresh_from_db()
    assert equipment.status == EquipmentStatus.AVAILABLE
    assert equipment.archived_at is None
    assert record.status == request_status


def test_archived_equipment_hidden_from_catalog_and_cannot_be_borrowed(auth_client, provider, borrower):
    equipment = EquipmentFactory(provider=provider)
    assert auth_client(provider).post(f"/api/equipment/{equipment.id}/archive").status_code == 200
    client = auth_client(borrower)
    for filters in (
        {},
        {"search": equipment.name},
        {"category": equipment.category_id},
        {"location": equipment.location_id},
        {"availability": "unavailable"},
    ):
        response = client.get("/api/equipment", filters)
        assert response.status_code == 200
        assert response.data["count"] == 0
    assert client.get(f"/api/equipment/{equipment.id}").status_code == 404
    response = client.post(
        reverse("borrow-request-list"),
        {
            "equipment_id": str(equipment.id),
            "pickup_date": str(timezone.localdate()),
            "due_date": str(timezone.localdate() + timedelta(days=1)),
            "purpose": "Research",
        },
        format="json",
    )
    assert response.status_code == 400
    assert not BorrowRequest.objects.exists()


def test_archived_equipment_cannot_be_restored_by_editing(auth_client, provider):
    equipment = EquipmentFactory(provider=provider)
    client = auth_client(provider)
    assert client.post(f"/api/equipment/{equipment.id}/archive").status_code == 200
    response = client.patch(f"/api/equipment/{equipment.id}", {"status": "AVAILABLE"}, format="json")
    assert response.status_code == 409
    assert Equipment.objects.get(pk=equipment.id).status == EquipmentStatus.ARCHIVED


def test_pending_request_cannot_be_approved_after_archive(auth_client, provider, borrower):
    equipment = EquipmentFactory(provider=provider)
    record = make_request(equipment, borrower, "PENDING")
    client = auth_client(provider)
    assert client.post(f"/api/equipment/{equipment.id}/archive").status_code == 200
    assert client.post(f"/api/provider/requests/{record.id}/approve").status_code == 409
    record.refresh_from_db()
    assert record.status == "PENDING"
