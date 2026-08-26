from __future__ import annotations

from apps.monitoring.discord import format_exception, send_discord_alert


class DiscordExceptionMiddleware:
    """Report uncaught Django exceptions to Discord (non-DRF views + fallthrough)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        send_discord_alert(
            source="api",
            title="Exception serveur Django",
            message=str(exception) or exception.__class__.__name__,
            path=request.get_full_path(),
            method=request.method,
            stack=format_exception(exception),
            extra={
                "exception": exception.__class__.__name__,
            },
        )
        return None
