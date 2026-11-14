from datetime import date, timedelta

import pytest

from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def request_for(borrower, provider, state=BorrowRequest.StatusChoices.APPROVED):
    equipment = EquipmentFactory(provider=provider, status=EquipmentStatus.AVAILABLE)
    req = BorrowRequest.objects.create(
        borrower=borrower,
        equipment=equipment,
        pickup_date=date.today() + timedelta(days=1),
        due_date=date.today() + timedelta(days=4),
        purpose="Microcontroller project",
        status=state,
    )
    return req, equipment


def borrower_url(req, action="checkout"):
    return f"/api/requests/borrow-requests/{req.id}/{action}/"


def provider_url(req, action="return"):
    return f"/api/provider/requests/{req.id}/{action}"


def test_borrower_checkout_then_provider_return_roundtrip(auth_client, borrower, provider):
    req, equipment = request_for(borrower, provider)
    borrower_client = auth_client(borrower)
    provider_client = auth_client(provider)

    checkout = borrower_client.post(borrower_url(req))
    req.refresh_from_db()
    equipment.refresh_from_db()
    assert checkout.status_code == 200
    assert checkout.data["status"] == "CHECKED_OUT"
    assert req.status == BorrowRequest.StatusChoices.CHECKED_OUT
    assert equipment.status == EquipmentStatus.CHECKED_OUT
    assert provider_client.get(f"/api/provider/requests/{req.id}").data["status"] == "CHECKED_OUT"

    returned = provider_client.post(provider_url(req), {"return_condition": "  Good condition; complete accessories.  "}, format="json")
    req.refresh_from_db()
    equipment.refresh_from_db()
    assert returned.status_code == 200
    assert returned.data["status"] == "RETURNED"
    assert returned.data["return_condition"] == "Good condition; complete accessories."
    assert returned.data["returned_at"] is not None
    assert req.status == BorrowRequest.StatusChoices.RETURNED
    assert equipment.status == EquipmentStatus.AVAILABLE
    assert borrower_client.get(f"/api/requests/borrow-requests/{req.id}/").data["return_condition"] == "Good condition; complete accessories."
    assert borrower_client.get("/api/requests/borrow-requests/mine/", {"status": "RETURNED"}).data["count"] == 1
    assert provider_client.get("/api/provider/requests", {"status": "RETURNED"}).data["count"] == 1


def test_pending_cannot_checkout(auth_client, borrower, provider):
    req, equipment = request_for(borrower, provider, BorrowRequest.StatusChoices.PENDING)
    response = auth_client(borrower).post(borrower_url(req))
    assert response.status_code == 409
    req.refresh_from_db()
    equipment.refresh_from_db()
    assert req.status == BorrowRequest.StatusChoices.PENDING
    assert equipment.status == EquipmentStatus.AVAILABLE


def test_borrower_cannot_checkout_others_request(auth_client, borrower, provider, other_provider):
    req, _ = request_for(borrower, provider)
    assert auth_client(other_provider).post(borrower_url(req)).status_code == 404


def test_provider_cannot_return_request_for_someone_elses_equipment(auth_client, borrower, provider, other_provider):
    req, _ = request_for(borrower, provider, BorrowRequest.StatusChoices.CHECKED_OUT)
    response = auth_client(other_provider).post(provider_url(req), {"return_condition": "Great"}, format="json")
    assert response.status_code == 404


@pytest.mark.parametrize("condition", ["", " ", "a" * 2001])
def test_return_requires_nonempty_condition_within_limit(auth_client, borrower, provider, condition):
    req, _ = request_for(borrower, provider, BorrowRequest.StatusChoices.CHECKED_OUT)
    response = auth_client(provider).post(provider_url(req), {"return_condition": condition}, format="json")
    req.refresh_from_db()
    assert response.status_code == 400
    assert req.status == BorrowRequest.StatusChoices.CHECKED_OUT


def test_cannot_return_before_checkout_or_twice(auth_client, borrower, provider):
    req, _ = request_for(borrower, provider)
    client = auth_client(provider)
    payload = {"return_condition": "No damage"}
    assert client.post(provider_url(req), payload, format="json").status_code == 409
    req.status = BorrowRequest.StatusChoices.CHECKED_OUT
    req.save(update_fields=["status"])
    assert client.post(provider_url(req), payload, format="json").status_code == 200
    assert client.post(provider_url(req), payload, format="json").status_code == 409


def test_checkout_rejects_unavailable_inventory(auth_client, borrower, provider):
    req, equipment = request_for(borrower, provider)
    equipment.status = EquipmentStatus.MAINTENANCE
    equipment.save(update_fields=["status"])
    assert auth_client(borrower).post(borrower_url(req)).status_code == 409
    req.refresh_from_db()
    assert req.status == BorrowRequest.StatusChoices.APPROVED


def test_borrower_cannot_forge_return_metadata(auth_client, borrower, provider):
    req, _ = request_for(borrower, provider, BorrowRequest.StatusChoices.PENDING)
    client = auth_client(borrower)
    response = client.patch(f"/api/requests/borrow-requests/{req.id}/", {
        "purpose": "Updated", "status": "RETURNED", "return_condition": "Unapproved",
    }, format="json")
    req.refresh_from_db()
    assert response.status_code == 200
    assert req.status == BorrowRequest.StatusChoices.PENDING
    assert req.return_condition == ""
