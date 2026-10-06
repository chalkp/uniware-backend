import uuid

from django.conf import settings
from django.db import models


class BorrowerRequest(models.Model):
    class StatusChoices(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"
        CHECKED_OUT = "CHECKED_OUT", "Checked Out"
        COMPLETED = "COMPLETED", "Completed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    borrower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrow_requests"
    )
    equipment = models.ForeignKey(
        "equipment.Equipment", on_delete=models.CASCADE, related_name="borrow_requests"
    )
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_borrow_requests",
    )

    pickup_date = models.DateField(help_text="Inclusive: first day of possession")
    due_date = models.DateField(help_text="Exclusive: handover-back day")
    purpose = models.TextField()

    status = models.CharField(max_length=20, choices=StatusChoices.choices, default=StatusChoices.PENDING)
    decision_reason = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(due_date__gte=models.F("pickup_date")),
                name="due_date_after_pickup_date",
            )
        ]

    def __str__(self):
        return f"Request {self.id} - {self.status}"
