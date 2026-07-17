from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class TelegramConfig:
    api_id: int
    api_hash: str
    channel_id: int
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
        session_path=session_path,
    )
