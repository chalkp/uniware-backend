import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.equipment.models import Category, Equipment, Location

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
