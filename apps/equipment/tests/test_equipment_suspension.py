from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountStatus
from apps.equipment.factories import EquipmentFactory
from apps.equipment.models import EquipmentStatus, EquipmentSuspensionNotice
from apps.requests.models import BorrowRequest

pytestmark = pytest.mark.django_db


def status_url(item):
    return f"/api/admin/equipment/{item.id}/suspension"


def request_for(borrower, item, state):
    return BorrowRequest.objects.create(
        borrower=borrower, equipment=item, pickup_date=date.today() + timedelta(days=1),
        due_date=date.today() + timedelta(days=3), purpose="Equipment lab", status=state,
    )


def test_admin_hold_blocks_new_requests_approval_and_checkout_but_preserves_history(
    auth_client, admin_user, provider, borrower
):
    item = EquipmentFactory(provider=provider)
    pending = request_for(borrower, item, BorrowRequest.StatusChoices.PENDING)
    approved = request_for(borrower, item, BorrowRequest.StatusChoices.APPROVED)
    admin = auth_client(admin_user)
    result = admin.patch(status_url(item), {"is_suspended": True, "reason": "Safety inspection"}, format="json")
    assert result.status_code == 200
    assert result.data["is_suspended"] is True
    assert result.data["suspension_reason"] == "Safety inspection"
    assert result.data["status"] == EquipmentStatus.AVAILABLE
    assert auth_client(provider).post(f"/api/provider/requests/{pending.id}/approve").status_code == 409
    assert auth_client(borrower).post(f"/api/requests/borrow-requests/{approved.id}/checkout/").status_code == 409
    create = auth_client(borrower).post("/api/requests/borrow-requests/", {
        "equipment_id": str(item.id), "pickup_date": str(date.today() + timedelta(days=5)),
        "due_date": str(date.today() + timedelta(days=7)), "purpose": "Another lab",
    }, format="json")
    assert create.status_code == 400 or create.status_code == 409
    pending.refresh_from_db(); approved.refresh_from_db()
    assert pending.status == "PENDING"
    assert approved.status == "APPROVED"
    assert EquipmentSuspensionNotice.objects.filter(recipient=borrower, equipment=item).exists()
    assert EquipmentSuspensionNotice.objects.filter(recipient=provider, equipment=item).exists()


def test_suspended_checked_out_equipment_can_be_returned_without_removing_hold(
    auth_client, admin_user, provider, borrower
):
    item = EquipmentFactory(provider=provider, status=EquipmentStatus.CHECKED_OUT)
    request = request_for(borrower, item, BorrowRequest.StatusChoices.CHECKED_OUT)
    admin = auth_client(admin_user)
    assert admin.patch(status_url(item), {"is_suspended": True, "reason": "Damaged"}, format="json").status_code == 200
    response = auth_client(provider).post(
        f"/api/provider/requests/{request.id}/return", {"return_condition": "Cracked screen"}, format="json"
    )
    assert response.status_code == 200
    item.refresh_from_db();request.refresh_from_db()
    assert item.status == EquipmentStatus.AVAILABLE
    assert item.is_suspended
    assert request.status == BorrowRequest.StatusChoices.RETURNED
    assert request.return_condition == "Cracked screen"


def test_reactivation_does_not_clear_manual_hold(auth_client, admin_user, provider, borrower):
    item = EquipmentFactory(provider=provider)
    admin = auth_client(admin_user)
    assert admin.patch(status_url(item), {"is_suspended": True, "reason": "Maintenance"}, format="json").status_code == 200
    assert admin.patch(f"/api/auth/users/{provider.id}/status", {"account_status": "SUSPENDED"}, format="json").status_code == 200
    assert admin.patch(f"/api/auth/users/{provider.id}/status", {"account_status": "ACTIVE"}, format="json").status_code == 200
    item.refresh_from_db()
    assert item.admin_suspended is True
    assert item.is_suspended
    assert item.suspension_reason == "Maintenance"
    assert admin.patch(status_url(item), {"is_suspended": False}, format="json").status_code == 200
    item.refresh_from_db()
    assert not item.is_suspended


def test_suspending_owner_suspends_every_owned_item_and_reactivating_restores_only_nonmanual(
    auth_client, admin_user, provider, borrower
):
    item = EquipmentFactory(provider=provider)
    manual = EquipmentFactory(provider=provider, admin_suspended=True, admin_suspension_reason="Missing parts")
    request_for(borrower, item, BorrowRequest.StatusChoices.PENDING)
    admin = auth_client(admin_user)
    response = admin.patch(f"/api/auth/users/{provider.id}/status", {"account_status": "SUSPENDED"}, format="json")
    assert response.status_code == 200
    provider.refresh_from_db()
    assert provider.account_status == AccountStatus.SUSPENDED
    item.refresh_from_db(); manual.refresh_from_db()
    assert item.is_suspended and manual.is_suspended
    assert auth_client(borrower).get(f"/api/equipment/{item.id}").data["is_suspended"] is True
    assert EquipmentSuspensionNotice.objects.filter(recipient=borrower, equipment=item).exists()
    assert admin.patch(f"/api/auth/users/{provider.id}/status", {"account_status": "ACTIVE"}, format="json").status_code == 200
    item.refresh_from_db(); manual.refresh_from_db()
    assert not item.is_suspended
    assert manual.is_suspended


def test_only_admin_can_manage_hold_and_reason_is_required(auth_client, admin_user, borrower, provider):
    item = EquipmentFactory(provider=provider)
    assert auth_client(borrower).patch(status_url(item), {"is_suspended": True, "reason": "No"}, format="json").status_code == 403
    assert auth_client(provider).patch(status_url(item), {"is_suspended": True, "reason": "No"}, format="json").status_code == 403
    admin = auth_client(admin_user)
    assert admin.patch(status_url(item), {"is_suspended": True, "reason": " "}, format="json").status_code == 400
    assert admin.patch(status_url(item), {"is_suspended": True, "reason": "Inspection"}, format="json").status_code == 200
    assert admin.get('/api/admin/equipment').status_code == 200
    assert auth_client(borrower).get('/api/admin/equipment').status_code == 403


def test_notices_are_scoped_to_recipient(auth_client, admin_user, provider, borrower):
    item = EquipmentFactory(provider=provider)
    admin = auth_client(admin_user)
    admin.patch(status_url(item), {"is_suspended": True, "reason": "Safety"}, format="json")
    borrower_items = auth_client(borrower).get('/api/notifications').data
    owner_items = auth_client(provider).get('/api/notifications').data
    assert borrower_items == []
    assert any(note['equipment_id'] == item.id for note in owner_items)
