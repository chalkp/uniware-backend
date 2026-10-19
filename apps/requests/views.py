from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import AccountStatus
from apps.common.exceptions import BookingConflict, InvalidStateTransition
from apps.common.permissions import IsProvider
from apps.equipment.models import Equipment, EquipmentStatus

from .models import BorrowRequest
from .serializers import (
    BorrowRequestSerializer,
    ProviderBorrowRequestSerializer,
    ProviderRequestListFilterSerializer,
    RejectionReasonSerializer,
)
from .services import check_equipment_availability


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
            "Retrieve the full details and current status of a specific borrow request using its ID. "
            "You can only view your own requests."
        ),
    ),
    partial_update=extend_schema(
        summary="Update a borrow request",
        description="Update a pending borrow request's dates, equipment, or purpose.",
    ),
)
class BorrowRequestViewSet(
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """US4-4, US4-5"""

    serializer_class = BorrowRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """US4-4, US4-5"""
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

    @extend_schema(
        summary="Cancel a borrow request",
        description=(
            "Transition a pending borrow request status to CANCELLED without deleting the database record"
        ),
    )
    @action(detail=True, methods=["post", "patch"], url_path="cancel")
    def cancel(self, request, pk=None):
        """US4-5"""
        borrow_request = self.get_object()

        if borrow_request.status != BorrowRequest.StatusChoices.PENDING:
            return Response(
                {"detail": "Only pending borrow requests can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        borrow_request.status = BorrowRequest.StatusChoices.CANCELLED
        borrow_request.save(update_fields=["status"])

        serializer = self.get_serializer(borrow_request)

        return Response(serializer.data)


class IsActiveProvider(IsProvider):
    message = "This action requires an active provider account."

    def has_permission(self, request, view):
        return bool(
            super().has_permission(request, view)
            and request.user.is_active
            and request.user.account_status == AccountStatus.ACTIVE
        )


@extend_schema_view(
    list=extend_schema(
        summary="List requests for my equipment",
        description="Returns requests made for equipment managed by the authenticated provider.",
        parameters=[OpenApiParameter("status", type=str, description="Filter by request status")],
    ),
    retrieve=extend_schema(
        summary="Get a request for my equipment",
        description="Returns 404 if the request is not managed by the authenticated provider.",
    ),
)
class ProviderBorrowRequestViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ProviderBorrowRequestSerializer
    permission_classes = [IsAuthenticated, IsActiveProvider]

    def get_queryset(self):
        queryset = BorrowRequest.objects.filter(equipment__provider=self.request.user).select_related(
            "borrower", "equipment", "equipment__category", "equipment__location", "decided_by"
        )
        if self.action in ("approve", "reject"):
            queryset = queryset.select_for_update(of=("self",))
        return queryset.order_by("pickup_date", "id")

    def list(self, request, *args, **kwargs):
        filters = ProviderRequestListFilterSerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = self.filter_queryset(self.get_queryset())
        requested_status = filters.validated_data.get("status")
        if requested_status and requested_status != "ALL":
            queryset = queryset.filter(status=requested_status)

        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    @extend_schema(summary="Approve a pending request for my equipment")
    @action(detail=True, methods=["post"], url_path="approve")
    @transaction.atomic
    def approve(self, request, pk=None):
        borrow_request = self.get_object()
        if borrow_request.status != BorrowRequest.StatusChoices.PENDING:
            raise InvalidStateTransition("Only pending requests can be approved.")

        equipment = Equipment.objects.select_for_update().get(pk=borrow_request.equipment_id)
        if equipment.status != EquipmentStatus.AVAILABLE or not check_equipment_availability(
            equipment.id, borrow_request.pickup_date, borrow_request.due_date
        ):
            raise BookingConflict("Equipment is no longer available for the requested period.")

        borrow_request.status = BorrowRequest.StatusChoices.APPROVED
        borrow_request.decision_reason = ""
        borrow_request.decided_by = request.user
        borrow_request.decided_at = timezone.now()
        borrow_request.save(update_fields=["status", "decision_reason", "decided_by", "decided_at"])
        return Response(self.get_serializer(borrow_request).data)

    @extend_schema(summary="Reject a pending request for my equipment")
    @action(detail=True, methods=["post"], url_path="reject")
    @transaction.atomic
    def reject(self, request, pk=None):
        borrow_request = self.get_object()
        if borrow_request.status != BorrowRequest.StatusChoices.PENDING:
            raise InvalidStateTransition("Only pending requests can be rejected.")

        reason_serializer = RejectionReasonSerializer(data=request.data)
        reason_serializer.is_valid(raise_exception=True)
        borrow_request.status = BorrowRequest.StatusChoices.REJECTED
        borrow_request.decision_reason = reason_serializer.validated_data["reason"]
        borrow_request.decided_by = request.user
        borrow_request.decided_at = timezone.now()
        borrow_request.save(update_fields=["status", "decision_reason", "decided_by", "decided_at"])
        return Response(self.get_serializer(borrow_request).data)
