from django.urls import path

from .views import LoginView, LogoutView, MeView, RegisterView, UserManagementView, UserStatusView

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("users", UserManagementView.as_view(), name="user-management-list"),
    path("users/<uuid:user_id>/roles", UserManagementView.as_view(), name="user-management-roles"),
    path("users/<uuid:user_id>/status", UserStatusView.as_view(), name="user-management-status"),
]
