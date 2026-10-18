from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.accounts.views import ProfileView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/auth/", include("apps.accounts.urls_auth")),
    path("api/profile", ProfileView.as_view(), name="profile"),
    path("api/", include("apps.equipment.urls")),
    path("api/requests/", include("apps.requests.urls")),
]
