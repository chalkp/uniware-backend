from rest_framework.routers import DefaultRouter

from .views import BorrowerRequestViewSet

router = DefaultRouter()
router.register(r"borrower-requests", BorrowerRequestViewSet, basename="borrower-request")

urlpatterns = router.urls
