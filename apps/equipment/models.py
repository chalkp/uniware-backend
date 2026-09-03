from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel, UUIDModel


class Category(UUIDModel):
    """US2-5"""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name


class Location(UUIDModel):
    """US2-5"""

    name = models.CharField(max_length=120, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class EquipmentStatus(models.TextChoices):
    AVAILABLE = "AVAILABLE", "Available"
    RESERVED = "RESERVED", "Reserved"
    CHECKED_OUT = "CHECKED_OUT", "Checked out"
    MAINTENANCE = "MAINTENANCE", "Maintenance"
    ARCHIVED = "ARCHIVED", "Archived"
    DISABLED = "DISABLED", "Disabled"


VISIBLE_TO_BORROWERS = [
    EquipmentStatus.AVAILABLE,
    EquipmentStatus.RESERVED,
    EquipmentStatus.CHECKED_OUT,
    EquipmentStatus.MAINTENANCE,
]

PROVIDER_SETTABLE_STATUSES = [EquipmentStatus.AVAILABLE, EquipmentStatus.MAINTENANCE]


class EquipmentQuerySet(models.QuerySet):
    def visible_to_borrowers(self):
        return self.filter(status__in=VISIBLE_TO_BORROWERS)


class Equipment(TimeStampedModel):
    """EPIC2/EPIC3 primary catalog entity"""

    asset_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=200)
    model = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="owned_equipment",
        on_delete=models.PROTECT,
    )
    category = models.ForeignKey(Category, related_name="equipment", on_delete=models.PROTECT)
    location = models.ForeignKey(Location, related_name="equipment", on_delete=models.PROTECT)

    status = models.CharField(
        max_length=16, choices=EquipmentStatus.choices, default=EquipmentStatus.AVAILABLE
    )

    archived_at = models.DateTimeField(null=True, blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    disabled_reason = models.TextField(blank=True, default="")

    objects = EquipmentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.asset_id} — {self.name}"
