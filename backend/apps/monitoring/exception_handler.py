from __future__ import annotations

from rest_framework.views import exception_handler as drf_exception_handler

from apps.monitoring.discord import format_exception, send_discord_alert


def discord_exception_handler(exc, context):
    """DRF handler: keep default responses, alert Discord on server errors."""
    response = drf_exception_handler(exc, context)

    request = context.get("request")
    path = ""
    method = ""
    if request is not None:
        path = getattr(request, "get_full_path", lambda: "")()
        method = getattr(request, "method", "") or ""

    status_code = response.status_code if response is not None else 500

    # Client errors (4xx) are expected; only escalate server failures.
    if status_code >= 500:
        send_discord_alert(
            source="api",
            title="Erreur API (5xx)",
            message=str(exc) or exc.__class__.__name__,
            path=path,
            method=method,
            status_code=status_code,
            stack=format_exception(exc),
            extra={"exception": exc.__class__.__name__},
        )

    return response
