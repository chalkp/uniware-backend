from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from apps.common.permissions import IsProvider, IsAdmin
from .suspension import notify_equipment_change

from .models import Category, Equipment, EquipmentStatus, EquipmentSuspensionNotice, Location
from .serializers import (
    CategorySerializer,
    EquipmentCatalogFilterSerializer,
    EquipmentSerializer,
    EquipmentSuspensionUpdateSerializer,
    LocationSerializer,
)


class EquipmentViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """US2-1, US2-3, US3-1, US3-4"""

    serializer_class = EquipmentSerializer

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update"):
            return [IsAuthenticated(), IsProvider()]
        return [IsAuthenticated()]

    def get_queryset(self):
        base = Equipment.objects.select_related("category", "location", "provider")
        if self.action in ("update", "partial_update"):
            return base.filter(provider=self.request.user)
        queryset = base.visible_to_borrowers()
        if self.action == "list":
            filters = EquipmentCatalogFilterSerializer(data=self.request.query_params)
            filters.is_valid(raise_exception=True)
            values = filters.validated_data
            if "category" in values:
                queryset = queryset.filter(category_id=values["category"])
            if "location" in values:
                queryset = queryset.filter(location_id=values["location"])
            if values.get("availability") == "available":
                queryset = queryset.filter(status=EquipmentStatus.AVAILABLE, admin_suspended=False, provider__account_status="ACTIVE", provider__is_active=True)
            elif values.get("availability") == "unavailable":
                queryset = queryset.exclude(status=EquipmentStatus.AVAILABLE, admin_suspended=False, provider__account_status="ACTIVE", provider__is_active=True)

            search_query = self.request.query_params.get("search", "").strip()
            if search_query:
                queryset = queryset.filter(Q(name__icontains=search_query) | Q(model__icontains=search_query))
        return queryset

    def perform_create(self, serializer):
        serializer.save(provider=self.request.user)


class ProviderEquipmentListView(generics.ListAPIView):
    """US2-2"""

    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated, IsProvider]

    def get_queryset(self):
        return Equipment.objects.filter(provider=self.request.user).select_related("category", "location", "provider")


class CategoryListView(generics.ListAPIView):
    """US2-5"""

    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class LocationListView(generics.ListAPIView):
    """US2-5"""

    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None


class AdminEquipmentListView(generics.ListAPIView):
    """Admin-only inventory across all providers, including archived items."""
    serializer_class = EquipmentSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        qs = Equipment.objects.select_related("provider", "category", "location").order_by("name", "id")
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(model__icontains=search) | Q(asset_id__icontains=search))
        return qs


class AdminEquipmentSuspensionView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @transaction.atomic
    def patch(self, request, equipment_id):
        payload = EquipmentSuspensionUpdateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        equipment = get_object_or_404(
            Equipment.objects.select_related("provider", "category", "location").select_for_update(), pk=equipment_id
        )
        before = equipment.is_suspended
        equipment.admin_suspended = payload.validated_data["is_suspended"]
        equipment.admin_suspension_reason = payload.validated_data.get("reason", "") if equipment.admin_suspended else ""
        equipment.admin_suspended_at = timezone.now() if equipment.admin_suspended else None
        equipment.save(update_fields=["admin_suspended", "admin_suspension_reason", "admin_suspended_at", "updated_at"])
        if before != equipment.is_suspended:
            notify_equipment_change(equipment, equipment.is_suspended, reason=equipment.suspension_reason)
        return Response(EquipmentSerializer(equipment).data, status=status.HTTP_200_OK)


class EquipmentNoticesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get(self, request, *args, **kwargs):
        notices = EquipmentSuspensionNotice.objects.filter(recipient=request.user).order_by("-created_at")[:20]
        return Response([
            {"id": item.pk, "message": item.message, "created_at": item.created_at, "equipment_id": item.equipment_id}
            for item in notices
        ])
