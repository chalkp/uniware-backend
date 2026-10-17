"""Integration coverage for provider API added for the combined frontend."""
from datetime import date, timedelta

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.requests.models import BorrowRequest


@pytest.fixture
def provider(db, available_equipment):
    user = available_equipment.provider
    user.is_provider = True
    user.save(update_fields=["is_provider"])
    return user


@pytest.fixture
def pending_request(db, available_equipment, borrower):
    return BorrowRequest.objects.create(
        borrower=borrower,
        equipment=available_equipment,
        pickup_date=date.today() + timedelta(days=2),
        due_date=date.today() + timedelta(days=5),
        purpose="Lab demonstration",
    )


@pytest.mark.django_db
def test_provider_can_see_only_requests_for_own_equipment(provider, pending_request, borrower, available_equipment):
    client = APIClient()
    client.force_authenticate(user=provider)
    response = client.get(reverse("provider-request-list"), {"status": "PENDING"})
    assert response.status_code == 200
    assert response.data["count"] == 1
    assert response.data["results"][0]["borrower"]["email"] == borrower.email
    assert str(response.data["results"][0]["id"]) == str(pending_request.id)

    outsider = User.objects.create_user("outsider@chula.ac.th", "password123", is_provider=True)
    client.force_authenticate(user=outsider)
    assert client.get(reverse("provider-request-detail", kwargs={"pk": pending_request.pk})).status_code == 404
    assert client.get(reverse("provider-request-list")).data["count"] == 0


@pytest.mark.django_db
def test_provider_decision_endpoints_do_not_exist(provider, pending_request):
    """Approval/rejection belongs to a future story, not this integration."""
    client = APIClient()
    client.force_authenticate(user=provider)
    for decision in ("approve", "reject"):
        response = client.post(f"/api/provider/requests/{pending_request.pk}/{decision}", {}, format="json")
        assert response.status_code == 404
    pending_request.refresh_from_db()
    assert pending_request.status == "PENDING"
