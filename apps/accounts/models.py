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
