from rest_framework import serializers

from apps.equipment.models import Equipment, EquipmentStatus
from apps.equipment.serializers import EquipmentSerializer

from .models import BorrowerRequest


class BorrowerRequestSerializer(serializers.ModelSerializer):
    """EPIC4-5: Serializer for submitting, viewing, and managing borrower requests."""

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
        model = BorrowerRequest
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

        if equipment:
            if getattr(equipment, "status", None) not in [
                EquipmentStatus.AVAILABLE,
                EquipmentStatus.RESERVED,
            ]:
                raise serializers.ValidationError(
                    {"equipment_id": "This equipment is currently not available for borrowing."}
                )

        if pickup_date and due_date and due_date < pickup_date:
            raise serializers.ValidationError({"due_date": "due_date must be on or after pickup_date."})

        return attrs
