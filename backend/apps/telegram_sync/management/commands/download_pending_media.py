import asyncio
import time

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from telethon.errors import RPCError

from apps.telegram_sync.downloader import download_pending_batch


class Command(BaseCommand):
    help = (
        "Download pending teaching media from Telegram and upload it to R2. "
        "Runs continuously in small batches to keep memory usage low."
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
            help="Seconds to sleep between batches (default 900 = 15 min).",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process a single batch and exit (useful for testing).",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        interval = options["interval"]
        run_once = options["once"]

        if batch_size <= 0:
            raise CommandError("--batch-size must be a positive integer.")
        if interval <= 0:
            raise CommandError("--interval must be a positive integer.")

        self.stdout.write(
            self.style.SUCCESS(
                f"Media worker started (batch-size={batch_size}, "
                f"interval={interval}s, once={run_once})."
            )
        )

        while True:
            try:
                stats = asyncio.run(
                    download_pending_batch(
                        batch_size=batch_size,
                        progress=self.stdout.write,
                    )
                )
            except ImproperlyConfigured as exc:
                raise CommandError(f"Configuration error: {exc}") from exc
            except (OSError, RPCError, RuntimeError, ValueError) as exc:
                self.stderr.write(self.style.ERROR(f"Batch failed: {exc}"))
                stats = None

            if stats is not None:
                if stats.claimed == 0:
                    self.stdout.write("No pending media.")
                else:
                    self.stdout.write(
                        f"Batch done: claimed={stats.claimed} "
                        f"uploaded={stats.uploaded} reused={stats.reused} "
                        f"failed={stats.failed}"
                    )

            if run_once:
                break

            time.sleep(interval)
