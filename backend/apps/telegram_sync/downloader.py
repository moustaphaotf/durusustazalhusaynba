from __future__ import annotations

import mimetypes
import tempfile
from dataclasses import dataclass
from pathlib import Path

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.teachings.models import Teaching
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import TelegramConfig, get_telegram_config
from apps.telegram_sync import storage


@dataclass(frozen=True)
class DownloadBatchStats:
    claimed: int = 0
    uploaded: int = 0
    failed: int = 0


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
def claim_pending_teachings(batch_size: int) -> list[Teaching]:
    """Atomically move up to `batch_size` pending teachings to PROCESSING."""
    teachings = list(
        Teaching.objects.select_for_update(skip_locked=True)
        .filter(download_status=Teaching.DownloadStatus.PENDING)
        .order_by("published_at", "telegram_message_id")[:batch_size]
    )
    ids = [t.pk for t in teachings]
    if ids:
        Teaching.objects.filter(pk__in=ids).update(
            download_status=Teaching.DownloadStatus.PROCESSING,
        )
    return teachings


def mark_ready(teaching: Teaching, storage_key: str) -> None:
    teaching.storage_key = storage_key
    teaching.download_status = Teaching.DownloadStatus.READY
    teaching.download_error = ""
    teaching.downloaded_at = timezone.now()
    teaching.save(
        update_fields=[
            "storage_key",
            "download_status",
            "download_error",
            "downloaded_at",
            "updated_at",
        ]
    )


def mark_failed(teaching: Teaching, error: str) -> None:
    teaching.download_status = Teaching.DownloadStatus.FAILED
    teaching.download_error = error[:2000]
    teaching.save(
        update_fields=["download_status", "download_error", "updated_at"]
    )


async def _process_teaching(client, teaching: Teaching) -> bool:
    """Download from Telegram then upload to R2. Returns True on success."""
    messages = await client.get_messages(
        teaching.telegram_channel_id,
        ids=teaching.telegram_message_id,
    )
    if messages is None or not getattr(messages, "media", None):
        await sync_to_async(mark_failed)(teaching, "Message or media not found.")
        return False

    extension = _media_extension(teaching, messages)
    content_type = _media_content_type(teaching, messages)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / f"{teaching.telegram_message_id}{extension}"

        downloaded = await messages.download_media(file=str(temp_path))
        if not downloaded:
            await sync_to_async(mark_failed)(teaching, "download_media returned empty.")
            return False

        key = _storage_key(teaching, extension)
        await sync_to_async(storage.upload_file)(
            str(downloaded),
            key,
            content_type=content_type,
        )
        await sync_to_async(mark_ready)(teaching, key)
        return True


async def download_pending_batch(
    *,
    batch_size: int,
    config: TelegramConfig | None = None,
) -> DownloadBatchStats:
    telegram_config = config or get_telegram_config()

    teachings = await sync_to_async(claim_pending_teachings)(batch_size)
    if not teachings:
        return DownloadBatchStats()

    uploaded = 0
    failed = 0

    client = create_telegram_client(telegram_config)
    await client.connect()
    try:
        if not await client.is_user_authorized():
            # Roll claimed items back to pending so a future run retries them.
            await sync_to_async(_reset_to_pending)(teachings)
            raise RuntimeError(
                "Telegram session is not authenticated. "
                "Run `python manage.py telegram_login` first."
            )

        for teaching in teachings:
            try:
                ok = await _process_teaching(client, teaching)
            except Exception as exc:  # noqa: BLE001 - persisted as failure state
                await sync_to_async(mark_failed)(teaching, repr(exc))
                failed += 1
                continue
            if ok:
                uploaded += 1
            else:
                failed += 1
    finally:
        await client.disconnect()

    return DownloadBatchStats(
        claimed=len(teachings),
        uploaded=uploaded,
        failed=failed,
    )


def _reset_to_pending(teachings: list[Teaching]) -> None:
    ids = [t.pk for t in teachings]
    Teaching.objects.filter(pk__in=ids).update(
        download_status=Teaching.DownloadStatus.PENDING,
    )
