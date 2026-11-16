from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.photos import PhotoSerializerMixin, process_photo
from apps.equipment.models import Equipment, EquipmentStatus
from apps.equipment.serializers import EquipmentSerializer

from .models import BorrowRequest, Checkout
from .services import check_equipment_availability

User = get_user_model()


class BorrowerSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "department", "account_status"]


class ProviderRequestListFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=tuple((choice.value, choice.label) for choice in BorrowRequest.StatusChoices)
        + (("ALL", "All"),),
        required=False,
    )


class ReturnConditionSerializer(serializers.Serializer):
    photo = serializers.FileField(required=False, write_only=True)

    def validate_photo(self, value):
        return process_photo(value)

    return_condition = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class RejectionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)


class CheckoutSerializer(serializers.ModelSerializer):
    handover_person = BorrowerSummarySerializer(read_only=True)

    class Meta:
        model = Checkout
        fields = ["checkout_at", "handover_person"]
        read_only_fields = fields


class BorrowRequestSerializer(serializers.ModelSerializer):
    checkout_record = CheckoutSerializer(read_only=True)

    def to_internal_value(self, data):
        if any(field in data for field in ("checkout_record", "checkout_at", "handover_person")):
            raise serializers.ValidationError(
                {"checkout_record": "Handover records cannot be supplied or modified."}
            )
        return super().to_internal_value(data)

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
            "checkout_record",
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
            "return_condition",
            "returned_at",
        ]
        read_only_fields = [
            "id",
            "borrower",
            "status",
            "decision_reason",
            "decided_by",
            "decided_at",
            "return_condition",
            "returned_at",
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
            # Effective suspension blocks new requests and edits without changing the request status.
            equipment = Equipment.objects.select_related("provider").get(pk=equipment.pk)
            if equipment.is_suspended and (not self.instance or equipment.id != self.instance.equipment_id):
                raise serializers.ValidationError(
                    {"equipment_id": "This equipment is suspended and cannot be requested or edited."}
                )
            if (not self.instance or equipment.id != self.instance.equipment_id) and getattr(
                equipment, "status", None
            ) not in [
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
                not self.instance or any(field in attrs for field in ("equipment", "pickup_date", "due_date"))
            )
            and not check_equipment_availability(equipment.id, pickup_date, due_date)
        ):
            raise serializers.ValidationError(
                {"non_field_errors": "The equipment is already booked during this date range."}
            )

        return attrs


class ProviderBorrowRequestSerializer(PhotoSerializerMixin, serializers.ModelSerializer):
    checkout_record = CheckoutSerializer(read_only=True)
    borrower = BorrowerSummarySerializer(read_only=True)
    equipment = EquipmentSerializer(read_only=True)
    decided_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = BorrowRequest
        fields = [
            "checkout_record",
            "id",
            "borrower",
            "equipment",
            "pickup_date",
            "photo_preview_url",
            "photo_original_url",
            "due_date",
            "purpose",
            "status",
            "decision_reason",
            "decided_by",
            "decided_at",
            "return_condition",
            "returned_at",
        ]
        read_only_fields = fields
