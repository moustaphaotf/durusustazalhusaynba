from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    channel_id: int
    channel_username: str
    session_path: Path


def get_telegram_config() -> TelegramConfig:
    missing = []
    if not settings.TELEGRAM_API_ID:
        missing.append("TELEGRAM_API_ID")
    if not settings.TELEGRAM_API_HASH:
        missing.append("TELEGRAM_API_HASH")

    if missing:
        variables = ", ".join(missing)
        raise ImproperlyConfigured(
            f"Missing Telegram configuration: {variables}. "
            "Set the variables in the root .env file."
        )

    session_path = Path(settings.TELEGRAM_SESSION_PATH)
    session_path.parent.mkdir(parents=True, exist_ok=True)

    return TelegramConfig(
        api_id=settings.TELEGRAM_API_ID,
        api_hash=settings.TELEGRAM_API_HASH,
        channel_id=settings.TELEGRAM_CHANNEL_ID,
        channel_username=(settings.TELEGRAM_CHANNEL_USERNAME or "").lstrip("@"),
        session_path=session_path,
    )


def build_message_url(
    *,
    message_id: int,
    channel_id: int,
    channel_username: str = "",
) -> str:
    if channel_username:
        return f"https://t.me/{channel_username}/{message_id}"

    # Private/public numeric form: -1001087177387 → 1087177387
    raw_id = str(channel_id)
    if raw_id.startswith("-100"):
        raw_id = raw_id[4:]
    elif raw_id.startswith("-"):
        raw_id = raw_id[1:]
    return f"https://t.me/c/{raw_id}/{message_id}"
