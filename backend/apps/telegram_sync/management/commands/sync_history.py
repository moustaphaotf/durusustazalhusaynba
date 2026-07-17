import asyncio

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon.errors import RPCError

from apps.telegram_sync.sync import sync_channel_history


class Command(BaseCommand):
    help = (
        "Synchronize historical audio messages from the configured Telegram channel."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of channel messages to scan (newest first).",
        )
        parser.add_argument(
            "--download",
            action="store_true",
            help="Download matched audio files into MEDIA_ROOT/teachings/.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scan and report matches without writing to the database.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit <= 0:
            raise CommandError("--limit must be a positive integer.")

        try:
            stats = asyncio.run(
                sync_channel_history(
                    limit=limit,
                    download=options["download"],
                    dry_run=options["dry_run"],
                )
            )
        except (ImproperlyConfigured, OSError, RPCError, RuntimeError, ValueError) as exc:
            raise CommandError(f"History synchronization failed: {exc}") from exc

        mode = "dry-run" if options["dry_run"] else "sync"
        self.stdout.write(self.style.SUCCESS(f"History {mode} completed."))
        self.stdout.write(f"Scanned: {stats.scanned}")
        self.stdout.write(f"Audio matched: {stats.matched}")
        self.stdout.write(f"Created: {stats.created}")
        self.stdout.write(f"Updated: {stats.updated}")
        self.stdout.write(f"Downloaded: {stats.downloaded}")
        self.stdout.write(f"Skipped (non-audio): {stats.skipped}")
