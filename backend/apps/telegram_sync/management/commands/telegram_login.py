import asyncio

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon.errors import RPCError

from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import get_telegram_config


class Command(BaseCommand):
    help = "Authenticate the configured Telegram account and persist its session."

    def handle(self, *args, **options):
        try:
            asyncio.run(self._login())
        except (ImproperlyConfigured, OSError, RPCError, ValueError) as exc:
            raise CommandError(f"Telegram authentication failed: {exc}") from exc

    async def _login(self):
        config = get_telegram_config()
        client = create_telegram_client(config)

        try:
            await client.start()
            account = await client.get_me()
            channel = await client.get_entity(config.channel_id)
        finally:
            await client.disconnect()

        account_name = account.username or account.first_name or str(account.id)
        channel_name = getattr(channel, "title", str(config.channel_id))
        self.stdout.write(
            self.style.SUCCESS(
                f"Authenticated as {account_name}; channel accessible: {channel_name}."
            )
        )
        self.stdout.write(f"Session saved to {config.session_path}.session")
