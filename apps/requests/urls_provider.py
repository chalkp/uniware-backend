from rest_framework.routers import DefaultRouter
from .views import ProviderBorrowRequestViewSet

router = DefaultRouter()
router.register(r"requests", ProviderBorrowRequestViewSet, basename="provider-request")

urlpatterns = router.urls