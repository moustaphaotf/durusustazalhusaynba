from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from asgiref.sync import sync_to_async
from django.conf import settings
from telethon.tl.custom.message import Message

from apps.teachings.models import Teaching
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import TelegramConfig, get_telegram_config
from apps.telegram_sync.messages import TeachingPayload, message_to_teaching_payload


@dataclass(frozen=True)
class SyncStats:
    scanned: int = 0
    matched: int = 0
    created: int = 0
    updated: int = 0
    downloaded: int = 0
    skipped: int = 0


def upsert_teaching(payload: TeachingPayload) -> tuple[Teaching, bool]:
    teaching, created = Teaching.objects.update_or_create(
        telegram_channel_id=payload.telegram_channel_id,
        telegram_message_id=payload.telegram_message_id,
        defaults={
            "title_ar": payload.title_ar,
            "title_fr": payload.title_fr,
            "description": payload.description,
            "media_type": payload.media_type,
            "telegram_file_id": payload.telegram_file_id,
            "file_name": payload.file_name,
            "file_size": payload.file_size,
            "published_at": payload.published_at,
        },
    )
    return teaching, created


def teaching_media_relative_path(payload: TeachingPayload) -> str:
    extension = Path(payload.file_name).suffix if payload.file_name else ".ogg"
    safe_name = f"{payload.telegram_message_id}{extension}"
    return str(Path("teachings") / safe_name)


async def _download_teaching_media(
    message: Message,
    payload: TeachingPayload,
) -> str | None:
    relative_path = teaching_media_relative_path(payload)
    absolute_path = Path(settings.MEDIA_ROOT) / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)

    downloaded = await message.download_media(file=str(absolute_path))
    if not downloaded:
        return None
    return relative_path


async def sync_channel_history(
    *,
    limit: int | None = None,
    download: bool = False,
    dry_run: bool = False,
    config: TelegramConfig | None = None,
) -> SyncStats:
    telegram_config = config or get_telegram_config()
    client = create_telegram_client(telegram_config)

    scanned = 0
    matched = 0
    created = 0
    updated = 0
    downloaded = 0
    skipped = 0

    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authenticated. "
                "Run `python manage.py telegram_login` first."
            )

        async for message in client.iter_messages(
            telegram_config.channel_id,
            limit=limit,
        ):
            scanned += 1
            payload = message_to_teaching_payload(
                message,
                telegram_config.channel_id,
            )
            if payload is None:
                skipped += 1
                continue

            matched += 1
            if dry_run:
                continue

            teaching, was_created = await sync_to_async(upsert_teaching)(payload)
            if was_created:
                created += 1
            else:
                updated += 1

            if download and message.media:
                relative_path = await _download_teaching_media(message, payload)
                if relative_path:
                    teaching.local_path = relative_path
                    await sync_to_async(teaching.save)(
                        update_fields=["local_path", "updated_at"]
                    )
                    downloaded += 1
    finally:
        await client.disconnect()

    return SyncStats(
        scanned=scanned,
        matched=matched,
        created=created,
        updated=updated,
        downloaded=downloaded,
        skipped=skipped,
    )
