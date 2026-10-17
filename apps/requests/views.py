from datetime import date

from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from apps.common.exceptions import InvalidStateTransition

from .models import BorrowRequest
from .serializers import BorrowRequestSerializer, BorrowRequestUpdateSerializer


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
    mixins.UpdateModelMixin,
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

    def get_object_for_update(self, pk):
        from django.shortcuts import get_object_or_404
        # queryset is restricted to the signed-in borrower's own requests.
        return get_object_or_404(
            BorrowRequest.objects.select_for_update().filter(borrower=self.request.user), pk=pk
        )

    def _check_can_manage(self):
        user = self.request.user
        if not user.is_borrower or user.account_status != "ACTIVE":
            raise PermissionDenied("Only active borrowers may modify requests.")

    @extend_schema(
        summary="Edit a pending borrow request",
        description="Only the owner can change pickup date, due date or purpose while pending and before pickup.",
        request=BorrowRequestUpdateSerializer,
        responses={200: BorrowRequestSerializer},
    )
    def partial_update(self, request, *args, **kwargs):
        self._check_can_manage()
        with transaction.atomic():
            item = self.get_object_for_update(kwargs["pk"])
            if item.status != BorrowRequest.StatusChoices.PENDING or item.pickup_date < date.today():
                raise InvalidStateTransition("Only pending requests before pickup can be edited.")
            serializer = BorrowRequestUpdateSerializer(item, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(BorrowRequestSerializer(item).data)

    # PUT (full update) is not supported; use PATCH for the editable fields.
    def update(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed
        raise MethodNotAllowed("PUT")

    @extend_schema(
        summary="Cancel my borrow request",
        description="Only the owner may cancel pending or approved requests before pickup. Cancellation preserves history.",
        request=None,
        responses={200: BorrowRequestSerializer},
    )
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        self._check_can_manage()
        with transaction.atomic():
            item = self.get_object_for_update(pk)
            if item.status not in (BorrowRequest.StatusChoices.PENDING, BorrowRequest.StatusChoices.APPROVED):
                raise InvalidStateTransition("Only pending or approved requests can be cancelled.")
            if item.pickup_date < date.today():
                raise InvalidStateTransition("Requests cannot be cancelled after pickup has begun.")
            item.status = BorrowRequest.StatusChoices.CANCELLED
            item.save(update_fields=["status"])
            return Response(BorrowRequestSerializer(item).data, status=status.HTTP_200_OK)

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
