from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    message = "This action requires admin capability."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsProvider(BasePermission):
    message = "This action requires provider capability."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_provider)


class IsBorrower(BasePermission):
    message = "This action requires borrower capability."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_borrower)
