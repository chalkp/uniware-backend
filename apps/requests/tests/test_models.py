from datetime import date, timedelta

import pytest

from apps.requests.models import BorrowRequest


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
