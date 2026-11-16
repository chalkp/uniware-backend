from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import ConsentRecord, User


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


@admin.register(ConsentRecord)
class ConsentRecordAdmin(admin.ModelAdmin):
    list_display = ["user", "consent_version", "granted_at", "ip_address"]
    search_fields = ["user__email", "consent_version", "consent_text_hash"]
    readonly_fields = [
        "id",
        "user",
        "consent_version",
        "consent_text_hash",
        "granted_at",
        "ip_address",
        "user_agent",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
