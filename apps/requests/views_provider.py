"""Read-only provider borrowing request inbox (approval is not yet implemented)."""

from rest_framework import generics
from rest_framework.exceptions import ValidationError

from apps.common.permissions import IsProvider
from .models import BorrowRequest
from .serializers import ProviderBorrowRequestSerializer


class ProviderRequestQuerysetMixin:
    permission_classes = [IsProvider]
    serializer_class = ProviderBorrowRequestSerializer

    def get_queryset(self):
        return (BorrowRequest.objects.filter(equipment__provider=self.request.user)
                .select_related("borrower", "equipment", "equipment__category",
                                "equipment__location", "decided_by")
                .order_by("-pickup_date", "-id"))


class ProviderRequestListView(ProviderRequestQuerysetMixin, generics.ListAPIView):
    """GET /api/provider/requests?status=PENDING&page=1"""

    def get_queryset(self):
        queryset = super().get_queryset()
        request_status = self.request.query_params.get("status")
        if request_status:
            valid = {value for value, _ in BorrowRequest.StatusChoices.choices}
            if request_status not in valid:
                raise ValidationError({"status": "Unknown borrow request status."})
            queryset = queryset.filter(status=request_status)
        return queryset


class ProviderRequestDetailView(ProviderRequestQuerysetMixin, generics.RetrieveAPIView):
    """GET /api/provider/requests/<uuid>"""
    lookup_field = "pk"


