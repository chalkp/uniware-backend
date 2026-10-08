from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

# Adjust these imports according to your actual app structure
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
def available_equipment(db):
    """Create dependencies and an AVAILABLE piece of equipment."""
    provider = User.objects.create_user(email="provider@chula.ac.th", password="password123")
    category = Category.objects.create(name="Electronics")
    location = Location.objects.create(name="Main Library")

    return Equipment.objects.create(
        asset_id="EQ-1001",
        name="MacBook Pro",
        provider=provider,
        category=category,
        location=location,
        status="AVAILABLE",
    )


@pytest.fixture
def checked_out_equipment(db, available_equipment):
    """Create a piece of equipment that is NOT requestable."""
    available_equipment.id = None
    available_equipment.asset_id = "EQ-1002"
    available_equipment.status = "CHECKED_OUT"
    available_equipment.save()
    return available_equipment


@pytest.mark.django_db
class TestBorrowRequestModel:
    def test_create_borrow_request_model(self, borrower, available_equipment):
        """Test the data model creation, relationships, and default status."""
        pickup = date.today()
        due = pickup + timedelta(days=3)

        request = BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=pickup,
            due_date=due,
            purpose="Project research",
        )

        assert request.id is not None
        assert request.borrower == borrower
        assert request.equipment == available_equipment
        # Status should default to PENDING
        assert request.status == BorrowRequest.StatusChoices.PENDING
        assert request.decision_reason == ""
        assert str(request) == f"Request {request.id} - PENDING"


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

    def test_create_request_invalid_dates(self, api_client, borrower, available_equipment):
        """Test API validates that due_date is on or after pickup_date."""
        api_client.force_authenticate(user=borrower)

        payload = {
            "equipment_id": str(available_equipment.id),
            "pickup_date": date.today().isoformat(),
            "due_date": (date.today() - timedelta(days=1)).isoformat(),  # Due before pickup
            "purpose": "Time travel",
        }

        response = api_client.post(self.get_url(), payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Access the custom error structure correctly
        error_details = response.data["error"]["details"]

        assert "due_date" in error_details
        assert error_details["due_date"][0] == "due_date must be on or after pickup_date."

    def test_create_request_unavailable_equipment(self, api_client, borrower, checked_out_equipment):
        """Test API prevents requesting equipment that is not AVAILABLE or RESERVED."""
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

        # FIX: Extract results from the paginated response
        # Using .get() ensures it still works if you ever turn pagination off
        results = response.data.get("results", response.data)

        assert len(results) == 2

        assert results[0]["id"] == str(req2.id)
        assert results[1]["id"] == str(req1.id)

    def test_get_mine_unauthenticated(self, api_client):
        """Test the 'mine' endpoint requires authentication."""
        url = reverse("borrow-request-mine")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
