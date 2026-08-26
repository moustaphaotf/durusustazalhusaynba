from django.urls import path

from apps.monitoring.views import ClientErrorReportView

urlpatterns = [
    path(
        "client-errors/",
        ClientErrorReportView.as_view(),
        name="client-error-report",
    ),
]
