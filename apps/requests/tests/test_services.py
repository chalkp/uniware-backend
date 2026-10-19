from datetime import date, timedelta

import pytest

from apps.requests.models import BorrowRequest
from apps.requests.services import check_equipment_availability


@pytest.mark.django_db
class TestEquipmentAvailabilityService:
    def test_check_availability_no_requests(self, available_equipment):
        """Equipment is available if there are no existing requests."""
        is_available = check_equipment_availability(
            available_equipment.id, date.today(), date.today() + timedelta(days=3)
        )
        assert is_available is True

    def test_check_availability_overlapping_approved(self, borrower, available_equipment):
        """Equipment is unavailable if dates overlap with an APPROVED request."""
        BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today() + timedelta(days=2),
            due_date=date.today() + timedelta(days=5),
            purpose="Already booked",
            status=BorrowRequest.StatusChoices.APPROVED,
        )

        # Overlapping dates
        assert (
            check_equipment_availability(
                available_equipment.id, date.today() + timedelta(days=3), date.today() + timedelta(days=6)
            )
            is False
        )

        # Non-overlapping dates (after)
        assert (
            check_equipment_availability(
                available_equipment.id, date.today() + timedelta(days=6), date.today() + timedelta(days=8)
            )
            is True
        )

    def test_check_availability_overlapping_pending(self, borrower, available_equipment):
        """Equipment is still available if overlapping request is only PENDING."""
        BorrowRequest.objects.create(
            borrower=borrower,
            equipment=available_equipment,
            pickup_date=date.today() + timedelta(days=2),
            due_date=date.today() + timedelta(days=5),
            purpose="Pending booking",
            status=BorrowRequest.StatusChoices.PENDING,
        )

        # Overlaps but shouldn't block
        assert (
            check_equipment_availability(
                available_equipment.id, date.today() + timedelta(days=3), date.today() + timedelta(days=6)
            )
            is True
        )
