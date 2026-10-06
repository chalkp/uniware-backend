from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .models import BorrowerRequest
from .serializers import BorrowerRequestSerializer


class BorrowerRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):

    serializer_class = BorrowerRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Borrowers should only view their own requests."""
        return (
            BorrowerRequest.objects.filter(borrower=self.request.user)
            .select_related(
                "borrower", "equipment", "equipment__category", "equipment__location", "decided_by"
            )
            .order_by("-pickup_date")
        )

    def perform_create(self, serializer):
        """Automatically assign the current logged-in user as borrower and default status to PENDING."""
        serializer.save(
            borrower=self.request.user,
            status=BorrowerRequest.StatusChoices.PENDING,
        )
