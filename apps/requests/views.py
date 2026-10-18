from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import BorrowRequest
from .serializers import BorrowRequestSerializer


@extend_schema_view(
    create=extend_schema(
        summary="Create a new borrow request",
        description=(
            "Submit a request to borrow a specific piece of equipment. "
            "The due date must be on or after the pickup date. "
            "The equipment must be AVAILABLE."
        ),
    ),
    retrieve=extend_schema(
        summary="Get borrow request details",
        description=(
            "Retrieve the full details and current status of a specific borrow request using its ID."
            "You can only view your own requests."
        ),
    ),
)
class BorrowRequestViewSet(
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = BorrowRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            BorrowRequest.objects.filter(borrower=self.request.user)
            .select_related(
                "borrower", "equipment", "equipment__category", "equipment__location", "decided_by"
            )
            .order_by("-pickup_date")
        )

    def perform_create(self, serializer):
        serializer.save(
            borrower=self.request.user,
            status=BorrowRequest.StatusChoices.PENDING,
        )

    @extend_schema(
        summary="List my borrow requests",
        description=(
            "Returns a list of all borrow requests made by the currently "
            "authenticated user, ordered by pickup date."
        ),
    )
    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
