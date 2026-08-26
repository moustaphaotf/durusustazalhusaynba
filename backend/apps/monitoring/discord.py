"""Send error alerts to a Discord incoming webhook.

Fails silently when DISCORD_WEBHOOK_URL is unset or Discord is unreachable,
so reporting never breaks the request path.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import traceback
import urllib.error
import urllib.request
from threading import Lock
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

_DEDUP_TTL_SECONDS = 60
_MAX_FIELD_LEN = 1000
_MAX_CONTENT_LEN = 1800

_recent_alerts: dict[str, float] = {}
_lock = Lock()


def _truncate(value: str, limit: int = _MAX_FIELD_LEN) -> str:
    value = value or ""
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _dedupe_key(source: str, message: str, path: str) -> str:
    raw = f"{source}|{message}|{path}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _should_skip(key: str) -> bool:
    now = time.monotonic()
    with _lock:
        expired = [k for k, ts in _recent_alerts.items() if now - ts > _DEDUP_TTL_SECONDS]
        for k in expired:
            del _recent_alerts[k]
        if key in _recent_alerts:
            return True
        _recent_alerts[key] = now
        return False


def format_exception(exc: BaseException) -> str:
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))


def send_discord_alert(
    *,
    source: str,
    title: str,
    message: str,
    path: str = "",
    method: str = "",
    status_code: int | None = None,
    stack: str = "",
    extra: dict[str, Any] | None = None,
) -> bool:
    """Post an embed to Discord. Returns True if a request was attempted successfully."""
    webhook = getattr(settings, "DISCORD_WEBHOOK_URL", "") or ""
    if not webhook:
        return False

    key = _dedupe_key(source, message, path)
    if _should_skip(key):
        logger.debug("Skipping duplicate Discord alert: %s", key[:12])
        return False

    fields = [
        {"name": "Source", "value": _truncate(source, 100), "inline": True},
    ]
    if method:
        fields.append({"name": "Method", "value": _truncate(method, 20), "inline": True})
    if path:
        fields.append({"name": "Path", "value": _truncate(path, 200), "inline": False})
    if status_code is not None:
        fields.append(
            {"name": "Status", "value": str(status_code), "inline": True},
        )
    if extra:
        for name, value in list(extra.items())[:5]:
            fields.append(
                {
                    "name": _truncate(str(name), 50),
                    "value": _truncate(str(value), 300),
                    "inline": False,
                }
            )
    if stack:
        fields.append(
            {
                "name": "Stack",
                "value": f"```\n{_truncate(stack, 900)}\n```",
                "inline": False,
            }
        )

    payload = {
        "username": "Durus Alerts",
        "embeds": [
            {
                "title": _truncate(title, 200),
                "description": _truncate(message, _MAX_CONTENT_LEN),
                "color": 0xC45C26,
                "fields": fields,
            }
        ],
    }

    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Durus-Monitor/1.0"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        logger.warning("Discord alert failed: %s", exc)
        return False
