import asyncio

from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon.errors import RPCError

from apps.telegram_sync.sync import sync_channel_history


class Command(BaseCommand):
    help = (
        "Synchronize audio message metadata from the configured Telegram channel. "
        "Default: historical scan (newest → oldest) from the saved cursor. "
        "Use --catch-up for a manual recent scan after newest_synced_message_id."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Maximum number of channel messages to scan in this run.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Scan and report matches without writing to the database.",
        )
        cursor_mode = parser.add_mutually_exclusive_group()
        cursor_mode.add_argument(
            "--reset",
            action="store_true",
            help="Ignore the saved cursor and restart history from the newest messages.",
        )
        cursor_mode.add_argument(
            "--catch-up",
            action="store_true",
            help=(
                "Manually scan only messages newer than the saved newest cursor. "
                "Does not change the historical oldest cursor."
            ),
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        if limit is not None and limit <= 0:
            raise CommandError("--limit must be a positive integer.")

        try:
            stats = asyncio.run(
                sync_channel_history(
                    limit=limit,
                    dry_run=options["dry_run"],
                    reset=options["reset"],
                    catch_up=options["catch_up"],
                )
            )
        except (ImproperlyConfigured, OSError, RPCError, RuntimeError, ValueError) as exc:
            raise CommandError(f"History synchronization failed: {exc}") from exc

        mode = "dry-run" if options["dry_run"] else "sync"
        scope = "Catch-up" if options["catch_up"] else "History"
        self.stdout.write(self.style.SUCCESS(f"{scope} {mode} completed."))
        self.stdout.write(f"Scanned: {stats.scanned}")
        self.stdout.write(f"Audio matched: {stats.matched}")
        self.stdout.write(f"Created (pending download): {stats.created}")
        self.stdout.write(f"Updated: {stats.updated}")
        self.stdout.write(f"Skipped (non-audio): {stats.skipped}")
        if options["catch_up"]:
            self.stdout.write(f"Catch-up after message ID: {stats.min_id}")
        else:
            self.stdout.write(f"Resume offset_id: {stats.offset_id}")
        self.stdout.write(f"Cursor oldest: {stats.oldest_synced_message_id}")
        self.stdout.write(f"Cursor newest: {stats.newest_synced_message_id}")
        if stats.history_complete:
            self.stdout.write(self.style.SUCCESS("History cursor marked complete."))
