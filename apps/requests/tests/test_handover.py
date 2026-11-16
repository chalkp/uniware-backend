from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.equipment.factories import EquipmentFactory
from apps.requests.models import BorrowRequest, Checkout

pytestmark = pytest.mark.django_db


def approved(borrower, provider, **kwargs):
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=EquipmentFactory(provider=provider),
        pickup_date=timezone.localdate(),
        due_date=timezone.localdate() + timedelta(days=2),
        purpose="Research",
        status=kwargs.pop("status", "APPROVED"),
        **kwargs,
    )


def url(record):
    return f"/api/provider/requests/{record.pk}/checkout"


def test_handover_audit_duplicate_and_return(auth_client, borrower, provider):
    record = approved(borrower, provider)
    client = auth_client(provider)
    before = timezone.now()
    response = client.post(url(record), {}, format="json")
    assert response.status_code == 200
    audit = Checkout.objects.get(request=record)
    assert before <= audit.checkout_at <= timezone.now()
    assert audit.handover_person == provider
    assert response.data["checkout_record"]["handover_person"]["id"] == str(provider.id)
    record.equipment.refresh_from_db()
    assert record.equipment.status == "CHECKED_OUT"
    assert client.post(url(record), {}, format="json").status_code == 409
    assert client.patch(f"/api/provider/requests/{record.id}", {"checkout_record": {}}).status_code == 405
    assert auth_client(borrower).get("/api/loans/mine?status=active").data["count"] == 1
    assert (
        client.post(
            f"/api/provider/requests/{record.id}/return", {"return_condition": "Good"}, format="json"
        ).status_code
        == 200
    )
    assert auth_client(borrower).get("/api/loans/mine?status=active").data["count"] == 0
    audit.refresh_from_db()
    assert audit.checkout_at >= before
    assert Checkout.objects.filter(request=record).count() == 1


def test_handover_permissions_and_tampering(auth_client, api_client, borrower, provider, other_provider):
    record = approved(borrower, provider)
    assert api_client.post(url(record)).status_code == 401
    assert auth_client(borrower).post(url(record)).status_code == 403
    assert (
        auth_client(borrower).post(f"/api/requests/borrow-requests/{record.pk}/checkout/").status_code == 403
    )
    assert auth_client(other_provider).post(url(record)).status_code == 404
    client = auth_client(provider)
    assert (
        client.post(
            url(record), {"checkout_at": "2000-01-01", "handover_person": str(borrower.pk)}, format="json"
        ).status_code
        == 400
    )
    assert not Checkout.objects.exists()


@pytest.mark.parametrize("state", ["PENDING", "REJECTED", "CHECKED_OUT", "RETURNED"])
def test_nonapproved_handover_denied(auth_client, borrower, provider, state):
    record = approved(borrower, provider, status=state)
    assert auth_client(provider).post(url(record), {}, format="json").status_code == 409
    assert not Checkout.objects.exists()


def test_pickup_scope_and_eligibility(auth_client, borrower, provider, other_provider):
    good = approved(borrower, provider)
    approved(borrower, other_provider)
    approved(borrower, provider, status="PENDING")
    blocked = approved(borrower, provider)
    blocked.equipment.admin_suspended = True
    blocked.equipment.save()
    expired = approved(borrower, provider)
    expired.pickup_date -= timedelta(days=1)
    expired.save()
    client = auth_client(provider)
    response = client.get("/api/provider/requests/ready-for-pickup")
    assert [item["id"] for item in response.data["results"]] == [str(good.id)]
    assert client.post(url(blocked), {}, format="json").status_code == 409
    assert client.post(url(expired), {}, format="json").status_code == 409
    assert auth_client(other_provider).get("/api/loans/mine?status=active").data["count"] == 0


def test_handover_rolls_back_on_save_failure(auth_client, borrower, provider):
    record = approved(borrower, provider)
    client = auth_client(provider)
    with patch("apps.equipment.models.Equipment.save", side_effect=RuntimeError("storage failure")):
        with pytest.raises(RuntimeError):
            client.post(url(record), {}, format="json")
    record.refresh_from_db()
    record.equipment.refresh_from_db()
    assert record.status == "APPROVED"
    assert record.equipment.status == "AVAILABLE"
    assert not Checkout.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_handover_has_one_winner(borrower, provider):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections
    from rest_framework.test import APIClient

    record = approved(borrower, provider)
    barrier = Barrier(2)

    def confirm():
        close_old_connections()
        try:
            client = APIClient()
            client.force_authenticate(user=provider)
            barrier.wait(timeout=10)
            return client.post(url(record), {}, format="json").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = [pool.submit(confirm) for _ in range(2)]
        assert sorted(attempt.result(timeout=20) for attempt in attempts) == [200, 409]
    assert Checkout.objects.filter(request=record).count() == 1
