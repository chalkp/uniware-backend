import hashlib
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from .validators import validate_university_email


class AccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_admin", False)
        extra_fields.setdefault("is_provider", False)
        extra_fields.setdefault("is_borrower", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_borrower", True)
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, validators=[validate_university_email])
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    department = models.CharField(max_length=255, blank=True, default="")

    is_admin = models.BooleanField(default=False)
    is_provider = models.BooleanField(default=False)
    is_borrower = models.BooleanField(default=True)

    account_status = models.CharField(
        max_length=16, choices=AccountStatus.choices, default=AccountStatus.ACTIVE
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]
    EDITABLE_PROFILE_FIELDS = ("first_name", "last_name", "department")

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


class ConsentRecord(models.Model):
    CURRENT_VERSION = "1.0"
    CURRENT_CONSENT_TEXT = (
        "I explicitly consent to the storage and processing of my personal data "
        "(name, university email, and department) for UniWare equipment borrowing."
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consent_records")
    consent_version = models.CharField(max_length=32)
    consent_text_hash = models.CharField(max_length=64)
    granted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-granted_at"]

    @classmethod
    def current_text_hash(cls) -> str:
        return hashlib.sha256(cls.CURRENT_CONSENT_TEXT.encode("utf-8")).hexdigest()

    def __str__(self):
        return f"{self.user.email} ({self.consent_version})"