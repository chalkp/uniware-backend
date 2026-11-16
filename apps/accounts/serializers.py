from collections.abc import Mapping

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from .models import AccountStatus, ConsentRecord, User
from .validators import validate_person_name, validate_university_email


def _create_consent_record(user: User, request=None) -> ConsentRecord:
    ip_address = None
    user_agent = ""
    if request is not None:
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
        raw_ip = forwarded_for.split(",")[0].strip() if forwarded_for else request.META.get("REMOTE_ADDR", "")
        ip_address = raw_ip or None
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    return ConsentRecord.objects.create(
        user=user,
        consent_version=ConsentRecord.CURRENT_VERSION,
        consent_text_hash=ConsentRecord.current_text_hash(),
        ip_address=ip_address,
        user_agent=user_agent,
    )


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = [
            "id",
            "consent_version",
            "consent_text_hash",
            "granted_at",
        ]
        read_only_fields = fields


class ConsentCreateSerializer(serializers.Serializer):
    data_storage_consent = serializers.BooleanField(write_only=True, required=True)

    def validate_data_storage_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent to personal data storage is required.")
        return value

    def create(self, validated_data):
        return _create_consent_record(
            user=self.context["request"].user,
            request=self.context.get("request"),
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "department",
            "is_admin",
            "is_provider",
            "is_borrower",
            "account_status",
            "date_joined",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    data_storage_consent = serializers.BooleanField(write_only=True, required=True)

    class Meta:
        model = User
        fields = [
            "email",
            "password",
            "first_name",
            "last_name",
            "department",
            "data_storage_consent",
        ]

    def validate_data_storage_consent(self, value):
        if not value:
            raise serializers.ValidationError("Consent to personal data storage is required.")
        return value

    def validate_first_name(self, value):
        return self._validate_name(value)

    def validate_last_name(self, value):
        return self._validate_name(value)

    @staticmethod
    def _validate_name(value):
        try:
            validate_person_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value.strip()

    def validate_email(self, value):
        value = value.strip().lower()
        try:
            validate_university_email(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        candidate = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("data_storage_consent")
        user = User.objects.create_user(password=password, **validated_data)
        _create_consent_record(user=user, request=self.context.get("request"))
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={"input_type": "password"})


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = UserSerializer.Meta.fields
        read_only_fields = tuple(field for field in fields if field not in User.EDITABLE_PROFILE_FIELDS)

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            errors = {
                field: ["This field may not be updated."]
                for field in data
                if field in self.fields and field not in User.EDITABLE_PROFILE_FIELDS
            }
            errors.update({field: ["Unknown field."] for field in data if field not in self.fields})
            if errors:
                raise serializers.ValidationError(errors)
        return super().to_internal_value(data)

    def validate_first_name(self, value):
        return self._validate_name(value)

    def validate_last_name(self, value):
        return self._validate_name(value)

    @staticmethod
    def _validate_name(value):
        try:
            validate_person_name(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
        return value.strip()

    def validate_department(self, value):
        return value.strip()


class UserRoleUpdateSerializer(serializers.ModelSerializer):
    """Restrict admin user management to capability flags only."""

    class Meta:
        model = User
        fields = ["is_admin", "is_provider", "is_borrower"]

    def to_internal_value(self, data):
        if not isinstance(data, Mapping) or set(data) - set(self.fields):
            raise serializers.ValidationError({"roles": "Supply only supported role fields."})
        if any(type(value) is not bool for value in data.values()):
            raise serializers.ValidationError({"roles": "Role values must be booleans."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if not any(key in attrs for key in self.fields):
            raise serializers.ValidationError("At least one role must be supplied.")
        return attrs


class UserStatusUpdateSerializer(serializers.ModelSerializer):
    """Administrator-only status change. Roles and personal information are not editable here."""

    account_status = serializers.ChoiceField(choices=AccountStatus.choices)

    class Meta:
        model = User
        fields = ["account_status"]

    def to_internal_value(self, data):
        if not isinstance(data, Mapping) or set(data.keys()) != {"account_status"}:
            raise serializers.ValidationError({"account_status": "Supply only the account_status field."})
        return super().to_internal_value(data)
