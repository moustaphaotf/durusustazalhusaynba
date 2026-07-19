import asyncio

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon import events
from telethon.errors import RPCError

from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import get_telegram_config
from apps.telegram_sync.downloader import (
    download_batch_with_client,
    has_priority_pending,
)
from apps.telegram_sync.messages import message_to_teaching_payload
from apps.telegram_sync.sync import record_live_message, upsert_teaching


class Command(BaseCommand):
    help = (
        "Long-running Telegram worker: listens for new channel messages "
        "(created as pending teachings) and downloads pending media — "
        "admin-requested downloads within seconds, full batches at a "
        "regular interval. Single process, single Telethon session."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=getattr(settings, "WORKER_BATCH_SIZE", 2),
            help="Number of teachings to process per batch (default 2).",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=getattr(settings, "WORKER_INTERVAL_SECONDS", 900),
            help="Seconds between full download batches (default 900 = 15 min).",
        )
        parser.add_argument(
            "--priority-poll",
            type=int,
            default=10,
            help=(
                "Seconds between checks for admin-requested downloads "
                "(default 10)."
            ),
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        interval = options["interval"]
        priority_poll = options["priority_poll"]

        if batch_size <= 0:
            raise CommandError("--batch-size must be a positive integer.")
        if interval <= 0:
            raise CommandError("--interval must be a positive integer.")
        if priority_poll <= 0:
            raise CommandError("--priority-poll must be a positive integer.")

        try:
            asyncio.run(self._run(batch_size, interval, priority_poll))
        except ImproperlyConfigured as exc:
            raise CommandError(f"Configuration error: {exc}") from exc

    async def _run(self, batch_size: int, interval: int, priority_poll: int):
        config = get_telegram_config()
        client = create_telegram_client(config)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                raise CommandError(
                    "Telegram session is not authenticated. "
                    "Run `python manage.py telegram_login` first."
                )

            channel = await client.get_entity(config.channel_id)

            async def on_new_message(event):
                await sync_to_async(record_live_message)(
                    config.channel_id,
                    event.message.id,
                )
                payload = message_to_teaching_payload(
                    event.message,
                    config.channel_id,
                    channel_username=config.channel_username,
                )
                if payload is None:
                    self.stdout.write(
                        f"Message {event.message.id}: no audio media, skipped."
                    )
                    return
                teaching, created = await sync_to_async(upsert_teaching)(payload)
                verb = "created" if created else "updated"
                self.stdout.write(
                    f"Message {event.message.id}: teaching #{teaching.pk} "
                    f"{verb} (pending download)."
                )

            client.add_event_handler(
                on_new_message,
                events.NewMessage(chats=channel),
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Telegram worker started (batch-size={batch_size}, "
                    f"interval={interval}s, priority-poll={priority_poll}s)."
                )
            )

            await asyncio.gather(
                client.run_until_disconnected(),
                self._download_loop(client, batch_size, interval, priority_poll),
            )
        finally:
            await client.disconnect()

    async def _download_loop(
        self,
        client,
        batch_size: int,
        interval: int,
        priority_poll: int,
    ):
        loop = asyncio.get_running_loop()
        next_full_batch = loop.time()  # first full batch right at startup

        while True:
            now = loop.time()
            full_batch_due = now >= next_full_batch
            priority_pending = await sync_to_async(has_priority_pending)()
            run_batch = full_batch_due or priority_pending
            # Priority-only wake: claim admin requests exclusively so a
            # single "download now" does not fill the batch with backlog.
            priority_only = priority_pending and not full_batch_due

            if run_batch:
                try:
                    stats = await download_batch_with_client(
                        client,
                        batch_size=batch_size,
                        progress=self.stdout.write,
                        priority_only=priority_only,
                    )
                except (OSError, RPCError, RuntimeError, ValueError) as exc:
                    self.stderr.write(self.style.ERROR(f"Batch failed: {exc}"))
                else:
                    if stats.claimed:
                        self.stdout.write(
                            f"Batch done: claimed={stats.claimed} "
                            f"uploaded={stats.uploaded} reused={stats.reused} "
                            f"failed={stats.failed}"
                        )
                if full_batch_due:
                    next_full_batch = now + interval

            await asyncio.sleep(priority_poll)
