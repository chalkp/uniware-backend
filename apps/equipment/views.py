from django.db.models import Q
from rest_framework import generics, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.common.permissions import IsProvider

from .models import Category, Equipment, EquipmentStatus, Location
from .serializers import (
    CategorySerializer,
    EquipmentCatalogFilterSerializer,
    EquipmentSerializer,
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
                queryset = queryset.filter(status=EquipmentStatus.AVAILABLE)
            elif values.get("availability") == "unavailable":
                queryset = queryset.exclude(status=EquipmentStatus.AVAILABLE)

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
        return Equipment.objects.filter(provider=self.request.user).select_related("category", "location")


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
