from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountStatus
from apps.equipment.factories import EquipmentFactory
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def make_request(borrower, provider):
    start = date.today() + timedelta(days=7)
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=EquipmentFactory(provider=provider),
        pickup_date=start,
        due_date=start + timedelta(days=2),
        purpose="Coursework",
    )


def test_provider_sees_suspended_flag_and_cannot_approve(auth_client, borrower, provider):
    request = make_request(borrower, provider)
    borrower.account_status = AccountStatus.SUSPENDED
    borrower.is_active = False
    borrower.save(update_fields=["account_status", "is_active"])
    client = auth_client(provider)
    listing = client.get("/api/provider/requests")
    detail = client.get(f"/api/provider/requests/{request.id}")
    approval = client.post(f"/api/provider/requests/{request.id}/approve", {}, format="json")

    assert listing.status_code == 200
    assert listing.data["results"][0]["borrower"]["account_status"] == "SUSPENDED"
    assert detail.status_code == 200
    assert detail.data["borrower"]["account_status"] == "SUSPENDED"
    assert approval.status_code == 409
    assert approval.data["error"]["code"] == "INVALID_STATE_TRANSITION"
    request.refresh_from_db()
    assert request.status == BorrowRequest.StatusChoices.PENDING


def test_provider_can_still_reject_suspended_borrower(auth_client, borrower, provider):
    request = make_request(borrower, provider)
    borrower.account_status = AccountStatus.SUSPENDED
    borrower.is_active = False
    borrower.save(update_fields=["account_status", "is_active"])
    response = auth_client(provider).post(
        f"/api/provider/requests/{request.id}/reject", {"reason": "Suspended account"}, format="json"
    )
    assert response.status_code == 200
    assert response.data["status"] == BorrowRequest.StatusChoices.REJECTED


def test_provider_can_approve_after_reactivation(auth_client, borrower, provider):
    request = make_request(borrower, provider)
    borrower.account_status = AccountStatus.SUSPENDED
    borrower.is_active = False
    borrower.save(update_fields=["account_status", "is_active"])
    client = auth_client(provider)
    assert client.post(f"/api/provider/requests/{request.id}/approve", {}, format="json").status_code == 409
    borrower.account_status = AccountStatus.ACTIVE
    borrower.is_active = True
    borrower.save(update_fields=["account_status", "is_active"])
    response = client.post(f"/api/provider/requests/{request.id}/approve", {}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == BorrowRequest.StatusChoices.APPROVED
