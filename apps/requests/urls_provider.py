from django.urls import path

from .views_provider import ProviderRequestDetailView, ProviderRequestListView

urlpatterns = [
    path("requests", ProviderRequestListView.as_view(), name="provider-request-list"),
    path("requests/<uuid:pk>", ProviderRequestDetailView.as_view(), name="provider-request-detail"),
]
