from django.contrib.auth import SESSION_KEY, authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .exceptions import InvalidCredentials
from .serializers import (
    LoginSerializer, ProfileSerializer, RegisterSerializer, UserSerializer,
    UserRoleUpdateSerializer, UserStatusUpdateSerializer,
)

from apps.common.permissions import IsAdmin
from apps.equipment.models import Equipment
from apps.equipment.suspension import notify_equipment_change
from .models import AccountStatus, User

class RegisterView(APIView):
    """US1-1"""

    permission_classes = [AllowAny]

    @extend_schema(request=RegisterSerializer, responses={201: UserSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        get_token(request)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """US1-2"""

    permission_classes = [AllowAny]

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active or user.account_status != AccountStatus.ACTIVE:
            raise InvalidCredentials("Invalid email or password.")
        django_login(request, user)
        get_token(request)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """US1-3"""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """US1-2, US1-3"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ProfileSerializer})
    def get(self, request):
        return Response(ProfileSerializer(request.user).data)

    @extend_schema(request=ProfileSerializer, responses={200: ProfileSerializer})
    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProfileSerializer(serializer.instance).data, status=status.HTTP_200_OK)

class UserManagementView(APIView):
    """US8-1, US8-2"""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        users = User.objects.all().order_by("email")
        return Response(UserSerializer(users, many=True).data)

    def patch(self, request, user_id):
        target = get_object_or_404(User, id=user_id)
        if target.id == request.user.id and request.data.get("is_admin") is False:
            return Response(
                {"detail": "You cannot remove your own admin role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = UserRoleUpdateSerializer(target, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(target).data, status=status.HTTP_200_OK)


class UserStatusView(APIView):
    """Allow administrators to suspend or reactivate other users."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(request=UserStatusUpdateSerializer, responses={200: UserSerializer})
    @transaction.atomic
    def patch(self, request, user_id):
        serializer = UserStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target = get_object_or_404(User.objects.select_for_update(), id=user_id)
        next_status = serializer.validated_data["account_status"]
        if target.id == request.user.id and next_status == AccountStatus.SUSPENDED:
            return Response(
                {"detail": "You cannot suspend your own administrator account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        was_suspended = target.account_status == AccountStatus.SUSPENDED or not target.is_active
        target.account_status = next_status
        # Django's ModelBackend denies login and invalidates existing sessions when
        # is_active is False, so suspension is effective immediately.
        target.is_active = next_status == AccountStatus.ACTIVE
        target.save(update_fields=["account_status", "is_active"])
        now_suspended = target.account_status == AccountStatus.SUSPENDED or not target.is_active
        if was_suspended != now_suspended:
            # All items owned by a suspended user become effectively suspended.
            # Manual admin holds are not cleared by owner reactivation.
            for equipment in Equipment.objects.filter(provider=target, admin_suspended=False).select_related("provider"):
                notify_equipment_change(equipment, now_suspended, reason=equipment.suspension_reason)
        if next_status == AccountStatus.SUSPENDED:
            # Database-backed sessions are configured in config/settings/base.py.
            # Invalidate all of this user's sessions so reactivation requires a new login.
            for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator():
                if session.get_decoded().get(SESSION_KEY) == str(target.id):
                    session.delete()
        return Response(UserSerializer(target).data, status=status.HTTP_200_OK)
