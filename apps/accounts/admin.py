from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = [
        "email",
        "first_name",
        "last_name",
        "is_admin",
        "is_provider",
        "is_borrower",
        "account_status",
    ]
    search_fields = ["email", "first_name", "last_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "department")}),
        (
            "Roles & status",
            {"fields": ("is_admin", "is_provider", "is_borrower", "account_status")},
        ),
        (
            "Django permissions",
            {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ["date_joined"]
