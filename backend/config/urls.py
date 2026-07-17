from django.contrib import admin
from django.urls import include, path

from config.health import health

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/", include("config.api_urls")),
]
