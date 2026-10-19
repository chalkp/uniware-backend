from rest_framework.routers import DefaultRouter

from .views import BorrowRequestViewSet, ProviderBorrowRequestViewSet

router = DefaultRouter()
router.register(r"borrow-requests", BorrowRequestViewSet, basename="borrow-request")
router.register(r"provider/requests", ProviderBorrowRequestViewSet, basename="provider-request")

urlpatterns = router.urls
