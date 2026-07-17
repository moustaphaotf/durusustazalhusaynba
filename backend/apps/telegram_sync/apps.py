from django.apps import AppConfig


class TelegramSyncConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.telegram_sync"
    label = "telegram_sync"
    verbose_name = "Telegram Sync"
