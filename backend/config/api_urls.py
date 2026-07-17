from rest_framework.routers import DefaultRouter

from apps.categories.views import CategoryViewSet
from apps.teachings.views import TeachingViewSet

router = DefaultRouter()
router.register("teachings", TeachingViewSet, basename="teaching")
router.register("categories", CategoryViewSet, basename="category")

urlpatterns = router.urls
