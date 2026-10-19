from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.equipment.models import Category, Equipment, Location
from apps.requests.models import BorrowRequest

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def borrower():
    """Create a standard borrower user."""
    return User.objects.create_user(email="borrower@chula.ac.th", password="password123", is_borrower=True)


@pytest.fixture
def other_borrower():
    """Create another borrower user for abuse testing."""
    return User.objects.create_user(email="borrower2@chula.ac.th", password="password123", is_borrower=True)


@pytest.fixture
def available_equipment(db):
    """Create dependencies and an AVAILABLE piece of equipment."""
    provider = User.objects.create_user(email="provider@chula.ac.th", password="password123")
    category = Category.objects.create(name="Electronics")
    location = Location.objects.create(name="Main Library")

    return Equipment.objects.create(
        asset_id="EQ-2001",
        name="Oscilloscope",
        provider=provider,
        category=category,
        location=location,
        status="AVAILABLE",
    )


@pytest.mark.django_db
class TestBorrowRequestEditAndCancelAPI:
    def get_detail_url(self, request_id):
        return reverse("borrow-request-detail", kwargs={"pk": str(request_id)})

    def get_cancel_url(self, request_id):
        return reverse("borrow-request-cancel", kwargs={"pk": str(request_id)})

    def test_patch_request_valid_success(self, api_client, borrower, available_equipment):
        """Test for US4-4: Valid PATCH successfully updates a pending borrow request"""
        api_client.force_authenticate(user=borrower)

        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Initial purpose",
        )

        url = self.get_detail_url(req.id)
        payload = {"purpose": "Updated advanced research purpose"}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        req.refresh_from_db()
        assert req.purpose == "Updated advanced research purpose"

    def test_patch_request_malformed_or_invalid_data(self, api_client, borrower, available_equipment):
        """Test for US4-4: Malformed or invalid data is rejected"""
        api_client.force_authenticate(user=borrower)

        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Valid purpose",
        )

        url = self.get_detail_url(req.id)
        # Malformed / invalid date constraint violation
        payload = {"due_date": (date.today() - timedelta(days=67)).isoformat()}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_request_non_pending_state_rejected(self, api_client, borrower, available_equipment):
        """Test for US4-4: Attempting to edit a non-pending borrow request must be rejected"""
        api_client.force_authenticate(user=borrower)

        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Approved request",
            status=BorrowRequest.StatusChoices.APPROVED,
        )

        url = self.get_detail_url(req.id)
        payload = {"purpose": "Trying to edit an approved request"}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_request_other_user_abuse(self, api_client, borrower, other_borrower, available_equipment):
        """Test for US4-4: A valid user trying to edit another user's borrow request is rejected"""
        req = BorrowRequest.objects.create(
            borrower=other_borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Other user's request",
        )

        api_client.force_authenticate(user=borrower)
        url = self.get_detail_url(req.id)
        payload = {"purpose": "Malicious edit attempt"}

        response = api_client.patch(url, payload, format="json")

        # Scoped queryset hides foreign records, returning a 404
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_request_unauthenticated_abuse(self, api_client, borrower, available_equipment):
        """Test for US4-4: Unauthenticated guest trying to edit a borrow request is rejected"""
        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Some request",
        )

        url = self.get_detail_url(req.id)
        payload = {"purpose": "Guest edit attempt"}

        response = api_client.patch(url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_cancel_request_success(self, api_client, borrower, available_equipment):
        """Test for US4-5: Successful cancellation transitions status to CANCELLED"""
        api_client.force_authenticate(user=borrower)
        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Need equipment",
            status=BorrowRequest.StatusChoices.PENDING,
        )

        url = self.get_cancel_url(req.id)
        response = api_client.post(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify the status is updated correctly and record is preserved in database
        req.refresh_from_db()
        assert req.status == BorrowRequest.StatusChoices.CANCELLED
        assert BorrowRequest.objects.filter(id=req.id).exists()

    def test_cancel_request_non_pending_rejected(self, api_client, borrower, available_equipment):
        """Test for US4-5: Trying to cancel a non-pending request is rejected."""
        api_client.force_authenticate(user=borrower)
        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Already approved",
            status=BorrowRequest.StatusChoices.APPROVED,
        )

        url = self.get_cancel_url(req.id)
        response = api_client.post(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        req.refresh_from_db()
        assert req.status == BorrowRequest.StatusChoices.APPROVED

    def test_deletion_abuse(self, api_client, borrower, available_equipment):
        """Test for US4-5: DELETE methods aren't allowed (US4-5)."""
        api_client.force_authenticate(user=borrower)
        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Preserved record",
        )

        url = self.get_detail_url(req.id)
        response = api_client.delete(url)

        # Deletion mixin is excluded, verifying that HTTP DELETE is blocked and record remains
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert BorrowRequest.objects.filter(id=req.id).exists()

    def test_cancel_non_existent_request(self, api_client, borrower):
        """Test for US4-5: Test that attempting to cancel a non-existent request ID returns 404 Not Found."""
        api_client.force_authenticate(user=borrower)
        fake_id = "how-do-you-cancel-a-nonexistent-request"
        url = self.get_cancel_url(fake_id)
        response = api_client.post(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_patch_request_non_existent_equipment(self, api_client, borrower, available_equipment):
        """Test for US4-4: Test that API prevents updating borrow requests to a non-existent eq."""
        api_client.force_authenticate(user=borrower)
        req = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=3),
            purpose="Initial purpose",
        )

        url = self.get_detail_url(req.id)
        payload = {"equipment_id": "does-this-thing-exist"}

        response = api_client.patch(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
