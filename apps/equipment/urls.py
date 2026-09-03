from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryListView, EquipmentViewSet, LocationListView, ProviderEquipmentListView

router = DefaultRouter(trailing_slash=False)
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = [
    path("provider/equipment", ProviderEquipmentListView.as_view(), name="provider-equipment-list"),
    path("categories", CategoryListView.as_view(), name="category-list"),
    path("locations", LocationListView.as_view(), name="location-list"),
    path("", include(router.urls)),
]
