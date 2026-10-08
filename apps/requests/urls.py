from rest_framework.routers import DefaultRouter

from .views import BorrowerRequestViewSet

router = DefaultRouter()
router.register(r"borrow-requests", BorrowerRequestViewSet, basename="borrower-request")

urlpatterns = router.urls
