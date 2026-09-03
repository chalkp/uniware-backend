from rest_framework import serializers

from .models import PROVIDER_SETTABLE_STATUSES, Category, Equipment, EquipmentStatus, Location


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "name"]


class EquipmentSerializer(serializers.ModelSerializer):
    """US2-1/US2-3/US2-5: create/edit serializer, also used read-only for the catalog
    and provider-inventory views."""

    category = CategorySerializer(read_only=True)
    location = LocationSerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        source="category", queryset=Category.objects.all(), write_only=True
    )
    location_id = serializers.PrimaryKeyRelatedField(
        source="location", queryset=Location.objects.all(), write_only=True
    )
    provider = serializers.PrimaryKeyRelatedField(read_only=True)
    status = serializers.ChoiceField(
        choices=[(s.value, s.label) for s in PROVIDER_SETTABLE_STATUSES],
        default=EquipmentStatus.AVAILABLE,
        required=False,
    )

    class Meta:
        model = Equipment
        fields = [
            "id",
            "asset_id",
            "name",
            "model",
            "description",
            "provider",
            "category",
            "location",
            "category_id",
            "location_id",
            "status",
            "archived_at",
            "disabled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "provider", "archived_at", "disabled_at", "created_at", "updated_at"]
