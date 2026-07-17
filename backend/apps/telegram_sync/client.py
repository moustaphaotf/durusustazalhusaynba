from telethon import TelegramClient

from apps.telegram_sync.config import TelegramConfig, get_telegram_config


def create_telegram_client(
    config: TelegramConfig | None = None,
) -> TelegramClient:
    telegram_config = config or get_telegram_config()

    return TelegramClient(
        str(telegram_config.session_path),
        telegram_config.api_id,
        telegram_config.api_hash,
    )
