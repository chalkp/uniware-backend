from datetime import date

from rest_framework import serializers

from apps.accounts.models import User
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
        pickup_date = attrs.get("pickup_date")
        due_date = attrs.get("due_date")
        equipment = attrs.get("equipment")

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

        if equipment and pickup_date and due_date:
            is_available = check_equipment_availability(equipment.id, pickup_date, due_date)
            if not is_available:
                raise serializers.ValidationError(
                    {"non_field_errors": "The equipment is already booked during this date range."}
                )

        return attrs


class ProviderBorrowerSerializer(serializers.ModelSerializer):
    """Only expose necessary borrower contact information to equipment owners."""

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "department"]


class ProviderBorrowRequestSerializer(BorrowRequestSerializer):
    borrower = ProviderBorrowerSerializer(read_only=True)

    class Meta(BorrowRequestSerializer.Meta):
        read_only_fields = BorrowRequestSerializer.Meta.fields


class BorrowRequestUpdateSerializer(serializers.ModelSerializer):
    """Only dates and purpose may be changed; equipment and decisions stay fixed."""

    purpose = serializers.CharField(allow_blank=False, trim_whitespace=True)

    class Meta:
        model = BorrowRequest
        fields = ["pickup_date", "due_date", "purpose"]

    def validate(self, attrs):
        unexpected = set(self.initial_data) - set(self.Meta.fields)
        if unexpected:
            raise serializers.ValidationError({field: "This field cannot be edited." for field in unexpected})
        # A partial PATCH must be checked with existing values for cross-field validation.
        values = {
            "pickup_date": attrs.get("pickup_date", self.instance.pickup_date),
            "due_date": attrs.get("due_date", self.instance.due_date),
            "equipment": self.instance.equipment,
        }
        BorrowRequestSerializer.validate(self, values)
        return attrs
