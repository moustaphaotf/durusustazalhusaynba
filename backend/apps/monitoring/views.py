from __future__ import annotations

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.monitoring.discord import send_discord_alert

_MAX_MESSAGE = 2000
_MAX_STACK = 4000
_MAX_URL = 500


class ClientErrorReportView(APIView):
    """Accept sanitized frontend error payloads and forward them to Discord."""

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}

        message = str(data.get("message") or "").strip()
        if not message:
            return Response(
                {"detail": "message is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stack = str(data.get("stack") or "")[:_MAX_STACK]
        url = str(data.get("url") or "")[:_MAX_URL]
        user_agent = str(data.get("userAgent") or request.META.get("HTTP_USER_AGENT", ""))[
            :300
        ]
        component = str(data.get("component") or "frontend")[:100]
        status_code = data.get("statusCode")
        try:
            parsed_status = int(status_code) if status_code is not None else None
        except (TypeError, ValueError):
            parsed_status = None

        send_discord_alert(
            source="frontend",
            title=f"Erreur frontend — {component}",
            message=message[:_MAX_MESSAGE],
            path=url,
            status_code=parsed_status,
            stack=stack,
            extra={
                "userAgent": user_agent,
                "component": component,
            },
        )

        return Response({"ok": True}, status=status.HTTP_202_ACCEPTED)
