from __future__ import annotations

import mimetypes
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from asgiref.sync import sync_to_async
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.teachings.models import Teaching
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import TelegramConfig, get_telegram_config
from apps.telegram_sync import storage


@dataclass(frozen=True)
class DownloadBatchStats:
    claimed: int = 0
    uploaded: int = 0
    reused: int = 0
    failed: int = 0


@dataclass(frozen=True)
class ProcessResult:
    ok: bool
    reused: bool = False


def _media_extension(teaching: Teaching, message) -> str:
    """Pick a file extension: file_name first, then Telegram file metadata."""
    if teaching.file_name:
        suffix = Path(teaching.file_name).suffix
        if suffix:
            return suffix

    file = getattr(message, "file", None)
    ext = getattr(file, "ext", "") or ""
    if ext and ext != ".unknown":
        return ext

    mime = getattr(file, "mime_type", "") or ""
    guessed = mimetypes.guess_extension(mime) if mime else None
    if guessed:
        return guessed

    if teaching.media_type == Teaching.MediaType.VOICE:
        return ".ogg"
    return ".mp3"


def _media_content_type(teaching: Teaching, message) -> str:
    """Pick a content type: Telegram mime_type first, then file_name guess."""
    file = getattr(message, "file", None)
    mime = getattr(file, "mime_type", "") or ""
    if mime:
        return mime

    if teaching.file_name:
        guessed, _ = mimetypes.guess_type(teaching.file_name)
        if guessed:
            return guessed

    if teaching.media_type == Teaching.MediaType.VOICE:
        return "audio/ogg"
    return "audio/mpeg"


def _storage_key(teaching: Teaching, extension: str) -> str:
    return (
        f"teachings/{teaching.telegram_channel_id}/"
        f"{teaching.telegram_message_id}{extension}"
    )


@transaction.atomic
def claim_pending_teachings(
    batch_size: int,
    *,
    priority_only: bool = False,
) -> list[Teaching]:
    """Atomically move up to `batch_size` pending teachings to PROCESSING.

    Admin-requested downloads (download_requested_at set) come first,
    oldest request first. Then newest publications, so the catalog
    (ordered by -published_at) fills with playable audio before older
    backlog items.

    When ``priority_only`` is True, only admin-requested teachings are
    claimed — used when the worker wakes solely for a priority request,
    so a single admin click does not pull unrelated backlog items.
    """
    queryset = Teaching.objects.select_for_update(skip_locked=True).filter(
        download_status=Teaching.DownloadStatus.PENDING,
    )
    if priority_only:
        queryset = queryset.filter(download_requested_at__isnull=False)
    teachings = list(
        queryset.order_by(
            F("download_requested_at").asc(nulls_last=True),
            "-published_at",
            "-telegram_message_id",
        )[:batch_size]
    )
    ids = [t.pk for t in teachings]
    if ids:
        Teaching.objects.filter(pk__in=ids).update(
            download_status=Teaching.DownloadStatus.PROCESSING,
        )
    return teachings


def has_priority_pending() -> bool:
    """True when an admin-requested download is waiting for the worker."""
    return Teaching.objects.filter(
        download_status=Teaching.DownloadStatus.PENDING,
        download_requested_at__isnull=False,
    ).exists()


def mark_ready(teaching: Teaching, storage_key: str) -> None:
    teaching.storage_key = storage_key
    teaching.download_status = Teaching.DownloadStatus.READY
    teaching.download_error = ""
    teaching.download_requested_at = None
    teaching.force_redownload = False
    teaching.downloaded_at = timezone.now()
    teaching.save(
        update_fields=[
            "storage_key",
            "download_status",
            "download_error",
            "download_requested_at",
            "force_redownload",
            "downloaded_at",
            "updated_at",
        ]
    )


def mark_failed(teaching: Teaching, error: str) -> None:
    teaching.download_status = Teaching.DownloadStatus.FAILED
    teaching.download_error = error[:2000]
    teaching.download_requested_at = None
    teaching.save(
        update_fields=[
            "download_status",
            "download_error",
            "download_requested_at",
            "updated_at",
        ]
    )


def try_reuse_existing_r2_object(teaching: Teaching) -> str | None:
    """Return an existing R2 key when a Telegram re-download can be skipped.

    Forced requeues bypass this check so admins can replace a corrupt object.
    """
    if teaching.force_redownload:
        return None
    return storage.find_existing_teaching_key(
        channel_id=teaching.telegram_channel_id,
        message_id=teaching.telegram_message_id,
        known_key=teaching.storage_key,
    )


async def _process_teaching(client, teaching: Teaching) -> ProcessResult:
    """Reuse R2 when possible, otherwise download from Telegram and upload."""
    existing_key = await sync_to_async(try_reuse_existing_r2_object)(teaching)
    if existing_key:
        await sync_to_async(mark_ready)(teaching, existing_key)
        return ProcessResult(ok=True, reused=True)

    messages = await client.get_messages(
        teaching.telegram_channel_id,
        ids=teaching.telegram_message_id,
    )
    if messages is None or not getattr(messages, "media", None):
        await sync_to_async(mark_failed)(teaching, "Message or media not found.")
        return ProcessResult(ok=False)

    extension = _media_extension(teaching, messages)
    content_type = _media_content_type(teaching, messages)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / f"{teaching.telegram_message_id}{extension}"

        downloaded = await messages.download_media(file=str(temp_path))
        if not downloaded:
            await sync_to_async(mark_failed)(teaching, "download_media returned empty.")
            return ProcessResult(ok=False)

        key = _storage_key(teaching, extension)
        await sync_to_async(storage.upload_file)(
            str(downloaded),
            key,
            content_type=content_type,
        )
        await sync_to_async(mark_ready)(teaching, key)
        return ProcessResult(ok=True, reused=False)


async def download_batch_with_client(
    client,
    *,
    batch_size: int,
    progress: Callable[[str], None] | None = None,
    priority_only: bool = False,
) -> DownloadBatchStats:
    """Process one batch using an already-connected, authorized client."""
    teachings = await sync_to_async(claim_pending_teachings)(
        batch_size,
        priority_only=priority_only,
    )
    if not teachings:
        return DownloadBatchStats()

    uploaded = 0
    reused = 0
    failed = 0

    for teaching in teachings:
        priority = teaching.download_requested_at is not None
        force = teaching.force_redownload
        if progress:
            progress(
                f"Download started: teaching={teaching.pk} "
                f"telegram_message={teaching.telegram_message_id} "
                f"priority={priority} force_redownload={force}"
            )
        try:
            result = await _process_teaching(client, teaching)
        except Exception as exc:  # noqa: BLE001 - persisted as failure state
            await sync_to_async(mark_failed)(teaching, repr(exc))
            failed += 1
            if progress:
                progress(
                    f"Download failed: teaching={teaching.pk} "
                    f"error={exc!r}"
                )
            continue
        if result.ok and result.reused:
            reused += 1
            if progress:
                progress(
                    f"R2 object reused: teaching={teaching.pk} "
                    f"storage_key={teaching.storage_key}"
                )
        elif result.ok:
            uploaded += 1
            if progress:
                progress(
                    f"Download completed: teaching={teaching.pk} "
                    f"storage_key={teaching.storage_key}"
                )
        else:
            failed += 1
            if progress:
                progress(
                    f"Download failed: teaching={teaching.pk} "
                    f"error={teaching.download_error}"
                )

    return DownloadBatchStats(
        claimed=len(teachings),
        uploaded=uploaded,
        reused=reused,
        failed=failed,
    )


async def download_pending_batch(
    *,
    batch_size: int,
    config: TelegramConfig | None = None,
    progress: Callable[[str], None] | None = None,
) -> DownloadBatchStats:
    telegram_config = config or get_telegram_config()

    # Avoid connecting to Telegram when there is nothing to do.
    has_pending = await sync_to_async(
        Teaching.objects.filter(
            download_status=Teaching.DownloadStatus.PENDING,
        ).exists
    )()
    if not has_pending:
        return DownloadBatchStats()

    client = create_telegram_client(telegram_config)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authenticated. "
                "Run `python manage.py telegram_login` first."
            )
        return await download_batch_with_client(
            client,
            batch_size=batch_size,
            progress=progress,
        )
    finally:
        await client.disconnect()
