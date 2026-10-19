from rest_framework.routers import SimpleRouter

from .views import ProviderBorrowRequestViewSet

router = SimpleRouter(trailing_slash=False)
router.register("provider/requests", ProviderBorrowRequestViewSet, basename="provider-request")

urlpatterns = router.urls
