from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountStatus
from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def make_request(borrower, equipment, *, status=BorrowRequest.StatusChoices.PENDING, start_offset=5):
    pickup_date = date.today() + timedelta(days=start_offset)
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=equipment,
        pickup_date=pickup_date,
        due_date=pickup_date + timedelta(days=3),
        purpose="Equipment for a university project",
        status=status,
    )


def provider_request_url(request_id=None, action=None):
    url = "/api/provider/requests"
    if request_id:
        url += f"/{request_id}"
    if action:
        url += f"/{action}"
    return url


def test_provider_request_list_is_scoped_and_filters_status(auth_client, borrower, provider, other_provider):
    equipment = EquipmentFactory(provider=provider)
    pending = make_request(borrower, equipment)
    make_request(borrower, equipment, status=BorrowRequest.StatusChoices.APPROVED, start_offset=10)
    other_equipment = EquipmentFactory(provider=other_provider)
    make_request(borrower, other_equipment)
    client = auth_client(provider)

    pending_response = client.get(provider_request_url(), {"status": "PENDING"})
    all_response = client.get(provider_request_url(), {"status": "ALL"})

    assert pending_response.status_code == 200
    assert pending_response.data["count"] == 1
    assert pending_response.data["results"][0]["id"] == str(pending.id)
    assert pending_response.data["results"][0]["borrower"]["email"] == borrower.email
    assert all_response.status_code == 200
    assert all_response.data["count"] == 2


def test_provider_can_retrieve_only_requests_for_owned_equipment(
    auth_client, borrower, provider, other_provider
):
    owned_request = make_request(borrower, EquipmentFactory(provider=provider))
    foreign_request = make_request(borrower, EquipmentFactory(provider=other_provider))
    client = auth_client(provider)

    own_response = client.get(provider_request_url(owned_request.id))
    foreign_response = client.get(provider_request_url(foreign_request.id))

    assert own_response.status_code == 200
    assert own_response.data["borrower"]["email"] == borrower.email
    assert foreign_response.status_code == 404


def test_provider_list_requires_active_provider(api_client, auth_client, borrower, provider):
    suspended_provider = provider
    suspended_provider.account_status = AccountStatus.SUSPENDED
    suspended_provider.save(update_fields=["account_status"])

    assert api_client.get(provider_request_url()).status_code == 401
    api_client.force_authenticate(user=borrower)
    assert api_client.get(provider_request_url()).status_code == 403
    assert auth_client(suspended_provider).get(provider_request_url()).status_code == 403


def test_provider_approval_records_decision_and_reserves_requested_period(auth_client, borrower, provider):
    equipment = EquipmentFactory(provider=provider, status=EquipmentStatus.AVAILABLE)
    request = make_request(borrower, equipment)

    response = auth_client(provider).post(provider_request_url(request.id, "approve"), {}, format="json")

    request.refresh_from_db()
    assert response.status_code == 200
    assert response.data["status"] == BorrowRequest.StatusChoices.APPROVED
    assert response.data["decided_by"] == provider.id
    assert response.data["decided_at"] is not None
    assert request.status == BorrowRequest.StatusChoices.APPROVED
    assert equipment.status == EquipmentStatus.AVAILABLE


def test_approval_rechecks_availability_and_leaves_conflicting_request_pending(
    auth_client, borrower, provider
):
    equipment = EquipmentFactory(provider=provider)
    target = make_request(borrower, equipment)
    make_request(
        borrower,
        equipment,
        status=BorrowRequest.StatusChoices.APPROVED,
        start_offset=6,
    )

    response = auth_client(provider).post(provider_request_url(target.id, "approve"), {}, format="json")

    target.refresh_from_db()
    assert response.status_code == 409
    assert response.data["error"]["code"] == "BOOKING_CONFLICT"
    assert target.status == BorrowRequest.StatusChoices.PENDING


def test_approval_rejects_unavailable_equipment_and_second_decisions(auth_client, borrower, provider):
    equipment = EquipmentFactory(provider=provider, status=EquipmentStatus.MAINTENANCE)
    request = make_request(borrower, equipment)
    client = auth_client(provider)

    unavailable_response = client.post(provider_request_url(request.id, "approve"), {}, format="json")
    equipment.status = EquipmentStatus.AVAILABLE
    equipment.save(update_fields=["status"])
    request.refresh_from_db()
    request.status = BorrowRequest.StatusChoices.APPROVED
    request.save(update_fields=["status"])
    second_decision_response = client.post(
        provider_request_url(request.id, "reject"), {"reason": "Late"}, format="json"
    )

    assert unavailable_response.status_code == 409
    assert unavailable_response.data["error"]["code"] == "BOOKING_CONFLICT"
    assert second_decision_response.status_code == 409
    assert second_decision_response.data["error"]["code"] == "INVALID_STATE_TRANSITION"


def test_provider_rejection_records_trimmed_reason(auth_client, borrower, provider):
    request = make_request(borrower, EquipmentFactory(provider=provider))

    response = auth_client(provider).post(
        provider_request_url(request.id, "reject"),
        {"reason": "  Item is required for maintenance.  "},
        format="json",
    )

    request.refresh_from_db()
    assert response.status_code == 200
    assert response.data["status"] == BorrowRequest.StatusChoices.REJECTED
    assert response.data["decision_reason"] == "Item is required for maintenance."
    assert response.data["decided_by"] == provider.id
    assert response.data["decided_at"] is not None
    assert request.decision_reason == "Item is required for maintenance."


@pytest.mark.parametrize("reason", ["", "   ", "x" * 2001])
def test_provider_rejection_requires_reason_within_limit(auth_client, borrower, provider, reason):
    request = make_request(borrower, EquipmentFactory(provider=provider))

    response = auth_client(provider).post(
        provider_request_url(request.id, "reject"), {"reason": reason}, format="json"
    )

    request.refresh_from_db()
    assert response.status_code == 400
    assert request.status == BorrowRequest.StatusChoices.PENDING


def test_provider_decisions_require_provider_ownership(auth_client, borrower, provider, other_provider):
    request = make_request(borrower, EquipmentFactory(provider=other_provider))

    response = auth_client(provider).post(provider_request_url(request.id, "approve"), {}, format="json")

    request.refresh_from_db()
    assert response.status_code == 404
    assert request.status == BorrowRequest.StatusChoices.PENDING
