from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from apps.requests.models import BorrowRequest

User = get_user_model()


@pytest.mark.django_db
class TestBorrowRequestAPI:
    def get_url(self):
        # Uses the router basename 'borrow-request'
        return reverse("borrow-request-list")

    def test_create_request_success(self, api_client, borrower, available_equipment):
        """Test POST API successfully creates a request with valid data."""
        api_client.force_authenticate(user=borrower)

        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
            "purpose": "Senior project presentation",
        }

        response = api_client.post(self.get_url(), payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == "PENDING"  # Automatically set
        assert response.data["borrower"] == borrower.id  # Automatically associated

        # Verify in DB
        assert BorrowRequest.objects.count() == 1
        req = BorrowRequest.objects.first()
        assert req.purpose == "Senior project presentation"

    def test_create_request_unauthenticated(self, api_client, available_equipment):
        """Test API requires an authenticated user."""
        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=1)).isoformat(),
            "purpose": "Testing",
        }

        response = api_client.post(self.get_url(), payload)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_request_missing_required_fields(self, api_client, borrower):
        """Test API validates required fields."""
        api_client.force_authenticate(user=borrower)
        payload = {}  # Empty payload

        response = api_client.post(self.get_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Access the custom error structure correctly
        error_details = response.data["error"]["details"]

        assert "equipment_id" in error_details
        assert "pickup_date" in error_details
        assert "due_date" in error_details
        assert "purpose" in error_details

    def test_create_request_past_pickup_date(self, api_client, borrower, available_equipment):
        """Test API validates that pickup_date cannot be in the past."""
        api_client.force_authenticate(user=borrower)

        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": (date.today() - timedelta(days=1)).isoformat(),  # Past date
            "due_date": (date.today() + timedelta(days=2)).isoformat(),  # Valid future date
            "purpose": "Testing pickup past date",
        }

        response = api_client.post(self.get_url(), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error_details = response.data["error"]["details"]
        assert "pickup_date" in error_details
        assert error_details["pickup_date"][0] == "Pickup date cannot be in the past."
        assert "due_date" not in error_details

    def test_create_request_past_due_date(self, api_client, borrower, available_equipment):
        """Test API validates that due_date cannot be in the past."""
        api_client.force_authenticate(user=borrower)

        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": date.today().isoformat(),  # Valid current date
            "due_date": (date.today() - timedelta(days=1)).isoformat(),  # Past date
            "purpose": "Testing due past date",
        }

        response = api_client.post(self.get_url(), payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error_details = response.data["error"]["details"]
        assert "due_date" in error_details
        assert error_details["due_date"][0] == "Due date cannot be in the past."

    def test_create_request_invalid_dates(self, api_client, borrower, available_equipment):
        """Test API validates that due_date is on or after pickup_date."""
        api_client.force_authenticate(user=borrower)

        # Uses future dates to isolate the `due_date < pickup_date` rule from the past date rule
        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": (date.today() + timedelta(days=2)).isoformat(),
            "due_date": (date.today() + timedelta(days=1)).isoformat(),  # Due before pickup
            "purpose": "Time travel backwards",
        }

        response = api_client.post(self.get_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Access the custom error structure correctly
        error_details = response.data["error"]["details"]

        assert "due_date" in error_details
        assert error_details["due_date"][0] == "due_date must be on or after pickup_date."

    def test_create_request_unavailable_equipment(self, api_client, borrower, checked_out_equipment):
        """Test API prevents requesting equipment that is not AVAILABLE."""
        api_client.force_authenticate(user=borrower)

        payload = {
            "equipment_id": str(checked_out_equipment.id),
            "pickup_date": date.today().isoformat(),
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
            "purpose": "Need this anyway",
        }

        response = api_client.post(self.get_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Access the custom error structure correctly
        error_details = response.data["error"]["details"]

        assert "equipment_id" in error_details
        assert error_details["equipment_id"][0] == "This equipment is currently not available for borrowing."

    def test_create_request_overlapping_availability(self, api_client, borrower, available_equipment):
        """Test API prevents booking if dates overlap with an APPROVED/CHECKED_OUT request."""
        # Create a blocking request
        BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today() + timedelta(days=1),
            due_date=date.today() + timedelta(days=5),
            purpose="Existing booking",
            status=BorrowRequest.StatusChoices.APPROVED,
        )

        api_client.force_authenticate(user=borrower)

        # Attempt to overlap
        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": (date.today() + timedelta(days=2)).isoformat(),
            "due_date": (date.today() + timedelta(days=4)).isoformat(),
            "purpose": "Overlap request",
        }

        response = api_client.post(self.get_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error_details = response.data["error"]["details"]
        assert "non_field_errors" in error_details
        assert (
            error_details["non_field_errors"][0] == "The equipment is already booked during this date range."
        )

    def test_get_mine_requests_success(self, api_client, borrower, available_equipment):
        """Test the 'mine' endpoint returns only the authenticated user's requests ordered by pickup_date."""
        api_client.force_authenticate(user=borrower)

        other_user = User.objects.create_user(email="other@chula.ac.th", password="password123")
        other_user.is_borrower = True
        other_user.save()

        req1 = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=2),
            purpose="My first request",
        )

        req2 = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today() + timedelta(days=5),
            due_date=date.today() + timedelta(days=7),
            purpose="My second request",
        )

        BorrowRequest.objects.create(
            borrower=other_user,
            equipment=available_equipment,
            pickup_date=date.today(),
            due_date=date.today() + timedelta(days=2),
            purpose="Someone else's request",
        )

        url = reverse("borrow-request-mine")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Extract results from the paginated response
        # Using .get() ensures it still works if pagination is turned off
        results = response.data.get("results", response.data)

        assert len(results) == 2

        assert results[0]["id"] == str(req2.id)
        assert results[1]["id"] == str(req1.id)

    def test_get_mine_unauthenticated(self, api_client):
        """Test the 'mine' endpoint requires authentication."""
        url = reverse("borrow-request-mine")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
