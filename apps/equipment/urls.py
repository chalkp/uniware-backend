from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (AdminEquipmentListView, AdminEquipmentSuspensionView, CategoryListView,
                    EquipmentNoticesView, EquipmentViewSet, LocationListView, ProviderEquipmentListView)

router = DefaultRouter(trailing_slash=False)
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = [
    path("admin/equipment", AdminEquipmentListView.as_view(), name="admin-equipment-list"),
    path("admin/equipment/<uuid:equipment_id>/suspension", AdminEquipmentSuspensionView.as_view(), name="admin-equipment-suspension"),
    path("notifications", EquipmentNoticesView.as_view(), name="equipment-notices"),
    path("provider/equipment", ProviderEquipmentListView.as_view(), name="provider-equipment-list"),
    path("categories", CategoryListView.as_view(), name="category-list"),
    path("locations", LocationListView.as_view(), name="location-list"),
    path("", include(router.urls)),
]
