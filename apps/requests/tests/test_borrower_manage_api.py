"""Borrower self-service requests: ownership, edits, cancellation and state safety."""
from datetime import date, timedelta

import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.requests.models import BorrowRequest


@pytest.fixture
def pending_request(db, borrower, available_equipment):
    return BorrowRequest.objects.create(
        borrower=borrower, equipment=available_equipment,
        pickup_date=date.today() + timedelta(days=3),
        due_date=date.today() + timedelta(days=7),
        purpose="Original reason", status=BorrowRequest.StatusChoices.PENDING,
    )


def detail_url(item):
    return reverse("borrow-request-detail", kwargs={"pk": item.pk})


def cancel_url(item):
    return reverse("borrow-request-cancel", kwargs={"pk": item.pk})


@pytest.mark.django_db
def test_edit_pending_request_fields_and_preserve_status(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    pickup = date.today() + timedelta(days=8)
    due = date.today() + timedelta(days=11)
    response = api_client.patch(detail_url(pending_request), {
        "pickup_date": pickup.isoformat(), "due_date": due.isoformat(), "purpose": "Updated reason",
    }, format="json")
    assert response.status_code == 200
    pending_request.refresh_from_db()
    assert pending_request.pickup_date == pickup
    assert pending_request.due_date == due
    assert pending_request.purpose == "Updated reason"
    assert pending_request.status == "PENDING"
    assert response.data["status"] == "PENDING"


@pytest.mark.django_db
def test_partial_edit_validates_combined_dates(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    response = api_client.patch(detail_url(pending_request), {
        "pickup_date": (pending_request.due_date + timedelta(days=1)).isoformat(),
    }, format="json")
    assert response.status_code == 400
    assert "due_date" in response.data["error"]["details"]
    pending_request.refresh_from_db()
    assert pending_request.purpose == "Original reason"


@pytest.mark.django_db
def test_edit_rejects_sensitive_fields(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    for data in ({"status": "APPROVED"}, {"equipment_id": str(pending_request.equipment_id)}):
        response = api_client.patch(detail_url(pending_request), data, format="json")
        assert response.status_code == 400
    pending_request.refresh_from_db()
    assert pending_request.status == "PENDING"


@pytest.mark.django_db
def test_cannot_edit_when_not_pending(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    for state in ("APPROVED", "REJECTED", "CANCELLED", "CHECKED_OUT", "COMPLETED"):
        pending_request.status = state
        pending_request.save(update_fields=["status"])
        response = api_client.patch(detail_url(pending_request), {"purpose": "Changed"}, format="json")
        assert response.status_code == 409


@pytest.mark.django_db
def test_cancel_pending_or_approved_and_keep_history(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    response = api_client.post(cancel_url(pending_request), {}, format="json")
    assert response.status_code == 200
    assert response.data["status"] == "CANCELLED"
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 409
    assert api_client.get(reverse("borrow-request-mine")).data["results"][0]["status"] == "CANCELLED"

    pending_request.status = "APPROVED"
    pending_request.save(update_fields=["status"])
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 200
    pending_request.refresh_from_db()
    assert pending_request.status == "CANCELLED"


@pytest.mark.django_db
def test_cannot_cancel_completed_rejected_or_checked_out(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    for state in ("REJECTED", "CHECKED_OUT", "COMPLETED"):
        pending_request.status = state
        pending_request.save(update_fields=["status"])
        assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 409


@pytest.mark.django_db
def test_no_edit_or_cancel_after_pickup(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    pending_request.pickup_date = date.today() - timedelta(days=1)
    pending_request.save(update_fields=["pickup_date"])
    assert api_client.patch(detail_url(pending_request), {"purpose": "new"}, format="json").status_code == 409
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 409


@pytest.mark.django_db
def test_other_borrowers_cannot_edit_or_cancel(api_client, borrower, pending_request):
    outsider = User.objects.create_user(email="different@chula.ac.th", password="password123")
    api_client.force_authenticate(user=outsider)
    assert api_client.patch(detail_url(pending_request), {"purpose": "Intrusion"}, format="json").status_code == 404
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 404
    pending_request.refresh_from_db()
    assert pending_request.purpose == "Original reason"


@pytest.mark.django_db
def test_active_borrower_role_required(api_client, borrower, pending_request):
    api_client.force_authenticate(user=borrower)
    borrower.is_borrower = False
    borrower.save(update_fields=["is_borrower"])
    assert api_client.patch(detail_url(pending_request), {"purpose": "New"}, format="json").status_code == 403
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 403
    borrower.is_borrower = True
    borrower.account_status = "SUSPENDED"
    borrower.save(update_fields=["is_borrower", "account_status"])
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 403


@pytest.mark.django_db
def test_unauthenticated_cannot_modify(api_client, pending_request):
    assert api_client.patch(detail_url(pending_request), {"purpose": "Intrusion"}, format="json").status_code == 401
    assert api_client.post(cancel_url(pending_request), {}, format="json").status_code == 401


@pytest.mark.django_db
def test_edit_checks_approved_booking_overlap(api_client, borrower, pending_request):
    BorrowRequest.objects.create(
        borrower=borrower, equipment=pending_request.equipment,
        pickup_date=pending_request.pickup_date + timedelta(days=10),
        due_date=pending_request.due_date + timedelta(days=10),
        purpose="Already reserved", status="APPROVED",
    )
    api_client.force_authenticate(user=borrower)
    response = api_client.patch(detail_url(pending_request), {
        "pickup_date": (pending_request.pickup_date + timedelta(days=11)).isoformat(),
        "due_date": (pending_request.due_date + timedelta(days=11)).isoformat(),
    }, format="json")
    assert response.status_code == 400
    assert "non_field_errors" in response.data["error"]["details"]


