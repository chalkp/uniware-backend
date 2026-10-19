from datetime import date

from rest_framework import serializers

from apps.equipment.models import Equipment, EquipmentStatus
from apps.equipment.serializers import EquipmentSerializer

from .models import BorrowRequest
from .services import check_equipment_availability


class BorrowRequestSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(read_only=True)
    equipment_id = serializers.PrimaryKeyRelatedField(
        source="equipment",
        queryset=Equipment.objects.all(),
        write_only=True,
    )

    borrower = serializers.PrimaryKeyRelatedField(read_only=True)
    decided_by = serializers.PrimaryKeyRelatedField(read_only=True)
    purpose = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = BorrowRequest
        fields = [
            "id",
            "borrower",
            "equipment",
            "equipment_id",
            "pickup_date",
            "due_date",
            "purpose",
            "status",
            "decision_reason",
            "decided_by",
            "decided_at",
        ]
        read_only_fields = [
            "id",
            "borrower",
            "status",
            "decision_reason",
            "decided_by",
            "decided_at",
        ]

    def validate(self, attrs):
        """US4-4"""
        # Ensure edits are only allowed when the request is in PENDING state
        if self.instance and self.instance.status != BorrowRequest.StatusChoices.PENDING:
            raise serializers.ValidationError(
                {"non_field_errors": "Only pending borrow requests can be edited."}
            )

        if self.instance:
            pickup_date = attrs.get("pickup_date", self.instance.pickup_date)
            due_date = attrs.get("due_date", self.instance.due_date)
        else:
            pickup_date = attrs.get("pickup_date")
            due_date = attrs.get("due_date")
        equipment = attrs.get("equipment")
        if equipment is None and self.instance:
            equipment = self.instance.equipment

        today = date.today()

        if pickup_date and pickup_date < today:
            raise serializers.ValidationError({"pickup_date": "Pickup date cannot be in the past."})

        if due_date and due_date < today:
            raise serializers.ValidationError({"due_date": "Due date cannot be in the past."})

        if pickup_date and due_date and due_date < pickup_date:
            raise serializers.ValidationError({"due_date": "due_date must be on or after pickup_date."})

        if equipment:
            if getattr(equipment, "status", None) not in [
                EquipmentStatus.AVAILABLE,
            ]:
                raise serializers.ValidationError(
                    {"equipment_id": "This equipment is currently not available for borrowing."}
                )

        if (
            equipment
            and pickup_date
            and due_date
            and (
                not self.instance
                or any(field in attrs for field in ("equipment", "pickup_date", "due_date"))
            )
            and not check_equipment_availability(equipment.id, pickup_date, due_date)
        ):
            raise serializers.ValidationError(
                {"non_field_errors": "The equipment is already booked during this date range."}
            )

        return attrs
