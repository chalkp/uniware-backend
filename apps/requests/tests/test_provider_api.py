from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from apps.equipment.models import Equipment
from apps.requests.models import BorrowRequest

User = get_user_model()


@pytest.mark.django_db
class TestProviderBorrowRequestAPI:
    def get_list_url(self):
        return reverse("provider-request-list")

    def get_detail_url(self, request_id):
        return reverse("provider-request-detail", kwargs={"pk": request_id})

    @pytest.fixture
    def provider_setup(self, borrower, available_equipment):
        """Sets up multiple providers, equipment, and requests to test scoping and leakage."""
        provider_a = available_equipment.provider
        provider_a.is_provider = True
        provider_a.save()

        # Create a second provider and their equipment
        provider_b = User.objects.create_user(
            email="provider_b@chula.ac.th", password="password123", is_provider=True
        )
        equip_b = Equipment.objects.create(
            asset_id="EQ-2001",
            name="Dell XPS",
            provider=provider_b,
            category=available_equipment.category,
            location=available_equipment.location,
            status="AVAILABLE",
        )

        # Provider A - PENDING Request
        req_a_pending = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=2),
            purpose="Provider A PENDING",
            status=BorrowRequest.StatusChoices.PENDING,
        )

        # Provider A - APPROVED Request
        req_a_approved = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today() + timedelta(days=5),
            due_date=date.today() + timedelta(days=7),
            purpose="Provider A APPROVED",
            status=BorrowRequest.StatusChoices.APPROVED,
        )

        # Provider B - PENDING Request
        req_b_pending = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=equip_b,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=2),
            purpose="Provider B PENDING",
            status=BorrowRequest.StatusChoices.PENDING,
        )

        return {
            "provider_a": provider_a,
            "provider_b": provider_b,
            "req_a_pending": req_a_pending,
            "req_a_approved": req_a_approved,
            "req_b_pending": req_b_pending,
        }

    def test_provider_access_only(self, api_client, borrower):
        """Test API requires the is_provider flag to be True."""
        # Authenticate as a standard borrower (is_provider=False)
        api_client.force_authenticate(user=borrower)

        response = api_client.get(self.get_list_url())
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_requests_scoping(self, api_client, provider_setup):
        """US5-1: Test list API strictly scopes returned requests to the provider's equipment."""
        provider_a = provider_setup["provider_a"]
        api_client.force_authenticate(user=provider_a)

        response = api_client.get(self.get_list_url())
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get("results", response.data)

        # Provider A should only see their 2 requests, entirely missing Provider B's request
        assert len(results) == 2
        returned_ids = {res["id"] for res in results}
        assert str(provider_setup["req_a_pending"].id) in returned_ids
        assert str(provider_setup["req_a_approved"].id) in returned_ids
        assert str(provider_setup["req_b_pending"].id) not in returned_ids

    def test_list_requests_status_filter(self, api_client, provider_setup):
        """US5-1: Test list API can filter to show only PENDING requests."""
        provider_a = provider_setup["provider_a"]
        api_client.force_authenticate(user=provider_a)

        url = f"{self.get_list_url()}?status=PENDING"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        results = response.data.get("results", response.data)

        # Provider A should now only see their 1 PENDING request
        assert len(results) == 1
        assert results[0]["id"] == str(provider_setup["req_a_pending"].id)
        assert results[0]["status"] == BorrowRequest.StatusChoices.PENDING

    def test_retrieve_request_success(self, api_client, provider_setup):
        """US5-2: Test retrieving detail view of an authorized request."""
        provider_a = provider_setup["provider_a"]
        req_a_pending = provider_setup["req_a_pending"]

        api_client.force_authenticate(user=provider_a)
        response = api_client.get(self.get_detail_url(req_a_pending.id))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(req_a_pending.id)
        assert response.data["purpose"] == req_a_pending.purpose

    def test_retrieve_request_unauthorized_leakage(self, api_client, provider_setup):
        """US5-2: Test retrieving another provider's request returns 404 Not Found, not 403."""
        provider_a = provider_setup["provider_a"]
        req_b_pending = provider_setup["req_b_pending"]

        # Authenticate as Provider A, but try to access Provider B's request
        api_client.force_authenticate(user=provider_a)
        response = api_client.get(self.get_detail_url(req_b_pending.id))

        # Must strictly be a 404 to obscure the request's existence
        assert response.status_code == status.HTTP_404_NOT_FOUND
