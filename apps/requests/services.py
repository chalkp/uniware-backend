from django.db.models import Q

from .models import BorrowRequest


def check_equipment_availability(equipment_id, pickup_date, due_date):
    """
    Checks if the equipment is available for the given date range.
    Returns True if available, False if there is an overlapping request.
    """
    blocking_statuses = [
        BorrowRequest.StatusChoices.APPROVED,
        BorrowRequest.StatusChoices.CHECKED_OUT,
    ]

    # Overlap Condition: (pickup_new < due_exist) AND (due_new > pickup_exist)
    overlapping_requests = BorrowRequest.objects.filter(
        equipment_id=equipment_id, status__in=blocking_statuses
    ).filter(Q(due_date__gt=pickup_date) & Q(pickup_date__lt=due_date))

    return not overlapping_requests.exists()
