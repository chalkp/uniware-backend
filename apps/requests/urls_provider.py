from rest_framework.routers import SimpleRouter

from .views import ProviderBorrowRequestViewSet

router = SimpleRouter(trailing_slash=False)
router.register(r"requests", ProviderBorrowRequestViewSet, basename="provider-request")

urlpatterns = router.urls
