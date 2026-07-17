import asyncio

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon.errors import RPCError

from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import get_telegram_config


class Command(BaseCommand):
    help = "Check the saved Telegram session and access to the configured channel."

    def handle(self, *args, **options):
        try:
            asyncio.run(self._check_status())
        except (ImproperlyConfigured, OSError, RPCError, ValueError) as exc:
            raise CommandError(f"Telegram status check failed: {exc}") from exc

    async def _check_status(self):
        config = get_telegram_config()
        client = create_telegram_client(config)

        try:
            await client.connect()
            if not await client.is_user_authorized():
                raise CommandError(
                    "Telegram session is not authenticated. "
                    "Run `python manage.py telegram_login` first."
                )

            account = await client.get_me()
            channel = await client.get_entity(config.channel_id)
        finally:
            await client.disconnect()

        account_name = account.username or account.first_name or str(account.id)
        channel_name = getattr(channel, "title", str(config.channel_id))
        self.stdout.write(self.style.SUCCESS("Telegram connection is operational."))
        self.stdout.write(f"Account: {account_name}")
        self.stdout.write(f"Channel: {channel_name} ({config.channel_id})")
