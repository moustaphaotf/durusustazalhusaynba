from __future__ import annotations

from dataclasses import dataclass

from asgiref.sync import sync_to_async
from django.utils import timezone

from apps.teachings.models import Teaching
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import TelegramConfig, get_telegram_config
from apps.telegram_sync.messages import TeachingPayload, message_to_teaching_payload
from apps.telegram_sync.models import ChannelSyncState


@dataclass(frozen=True)
class SyncStats:
    scanned: int = 0
    matched: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    offset_id: int | None = None
    min_id: int | None = None
    oldest_synced_message_id: int | None = None
    newest_synced_message_id: int | None = None
    history_complete: bool = False


def upsert_teaching(payload: TeachingPayload) -> tuple[Teaching, bool]:
    """Create or update a Teaching without clobbering download progress.

    New records start as PENDING so the media worker can pick them up.
    Existing records keep their current download_status / storage_key.
    """
    defaults = {
        "telegram_message_url": payload.telegram_message_url,
        "title_ar": payload.title_ar,
        "title_fr": payload.title_fr,
        "description": payload.description,
        "media_type": payload.media_type,
        "telegram_file_id": payload.telegram_file_id,
        "file_name": payload.file_name,
        "file_size": payload.file_size,
        "published_at": payload.published_at,
    }
    teaching, created = Teaching.objects.update_or_create(
        telegram_channel_id=payload.telegram_channel_id,
        telegram_message_id=payload.telegram_message_id,
        defaults=defaults,
    )
    if created:
        teaching.download_status = Teaching.DownloadStatus.PENDING
        teaching.save(update_fields=["download_status"])
    return teaching, created


def get_or_create_sync_state(channel_id: int) -> ChannelSyncState:
    state, _ = ChannelSyncState.objects.get_or_create(channel_id=channel_id)
    return state


def record_live_message(channel_id: int, message_id: int) -> ChannelSyncState:
    """Advance the newest-message cursor when the live listener sees a message.

    Keeps `sync_history` coherent: messages already captured live won't
    look like a gap above the recorded newest id.
    """
    state = get_or_create_sync_state(channel_id)
    if (
        state.newest_synced_message_id is None
        or message_id > state.newest_synced_message_id
    ):
        state.newest_synced_message_id = message_id
    state.last_synced_at = timezone.now()
    state.save(update_fields=["newest_synced_message_id", "last_synced_at"])
    return state


def advance_recent_sync_state(
    state: ChannelSyncState,
    *,
    scanned_ids: list[int],
) -> ChannelSyncState:
    """Advance only the recent-message cursor after a manual catch-up."""
    if scanned_ids:
        batch_max = max(scanned_ids)
        if (
            state.newest_synced_message_id is None
            or batch_max > state.newest_synced_message_id
        ):
            state.newest_synced_message_id = batch_max
    state.last_synced_at = timezone.now()
    state.save(update_fields=["newest_synced_message_id", "last_synced_at"])
    return state


def history_offset_id(state: ChannelSyncState) -> int | None:
    """Telethon offset_id to continue older history, or None to start from newest."""
    return state.oldest_synced_message_id


def catch_up_min_id(state: ChannelSyncState) -> int:
    """Message id after which a manual catch-up should resume."""
    if state.newest_synced_message_id is None:
        raise ValueError(
            "No newest message cursor exists yet. "
            "Run sync_history normally before using --catch-up."
        )
    return state.newest_synced_message_id


def history_iter_kwargs(
    *,
    limit: int | None,
    catch_up: bool,
    min_id: int | None,
    offset_id: int | None,
) -> dict:
    """Build Telethon iter_messages kwargs for history or catch-up."""
    kwargs: dict = {"limit": limit}
    if catch_up:
        # Oldest → newest keeps the cursor resumable when --limit is used.
        kwargs.update({"min_id": min_id, "reverse": True})
    elif offset_id is not None:
        kwargs["offset_id"] = offset_id
    return kwargs


def reset_sync_state(state: ChannelSyncState) -> ChannelSyncState:
    state.newest_synced_message_id = None
    state.oldest_synced_message_id = None
    state.history_complete = False
    state.last_synced_at = timezone.now()
    state.save(
        update_fields=[
            "newest_synced_message_id",
            "oldest_synced_message_id",
            "history_complete",
            "last_synced_at",
        ]
    )
    return state


def advance_sync_state(
    state: ChannelSyncState,
    *,
    scanned_ids: list[int],
) -> ChannelSyncState:
    """Update cursor after a history batch (newest → oldest)."""
    if not scanned_ids:
        if state.oldest_synced_message_id is not None:
            state.history_complete = True
        state.last_synced_at = timezone.now()
        state.save(update_fields=["history_complete", "last_synced_at"])
        return state

    batch_min = min(scanned_ids)
    batch_max = max(scanned_ids)

    if state.newest_synced_message_id is None:
        state.newest_synced_message_id = batch_max
    else:
        state.newest_synced_message_id = max(
            state.newest_synced_message_id,
            batch_max,
        )

    if state.oldest_synced_message_id is None:
        state.oldest_synced_message_id = batch_min
    else:
        state.oldest_synced_message_id = min(
            state.oldest_synced_message_id,
            batch_min,
        )

    state.history_complete = False
    state.last_synced_at = timezone.now()
    state.save(
        update_fields=[
            "newest_synced_message_id",
            "oldest_synced_message_id",
            "history_complete",
            "last_synced_at",
        ]
    )
    return state


async def sync_channel_history(
    *,
    limit: int | None = None,
    dry_run: bool = False,
    reset: bool = False,
    catch_up: bool = False,
    config: TelegramConfig | None = None,
) -> SyncStats:
    if reset and catch_up:
        raise ValueError("--reset and --catch-up cannot be used together.")

    telegram_config = config or get_telegram_config()
    client = create_telegram_client(telegram_config)

    scanned = 0
    matched = 0
    created = 0
    updated = 0
    skipped = 0
    scanned_ids: list[int] = []

    state = await sync_to_async(get_or_create_sync_state)(telegram_config.channel_id)
    min_id = None
    if catch_up:
        min_id = catch_up_min_id(state)
        offset_id = None
    elif reset and not dry_run:
        state = await sync_to_async(reset_sync_state)(state)
        offset_id = None
    else:
        offset_id = None if reset else history_offset_id(state)

    await client.connect()
    try:
        if not await client.is_user_authorized():
            raise RuntimeError(
                "Telegram session is not authenticated. "
                "Run `python manage.py telegram_login` first."
            )

        iter_kwargs = history_iter_kwargs(
            limit=limit,
            catch_up=catch_up,
            min_id=min_id,
            offset_id=offset_id,
        )

        async for message in client.iter_messages(
            telegram_config.channel_id,
            **iter_kwargs,
        ):
            scanned += 1
            scanned_ids.append(message.id)
            payload = message_to_teaching_payload(
                message,
                telegram_config.channel_id,
                channel_username=telegram_config.channel_username,
            )
            if payload is None:
                skipped += 1
                continue

            matched += 1
            if dry_run:
                continue

            _, was_created = await sync_to_async(upsert_teaching)(payload)
            if was_created:
                created += 1
            else:
                updated += 1
    finally:
        await client.disconnect()

    if not dry_run:
        if catch_up:
            state = await sync_to_async(advance_recent_sync_state)(
                state,
                scanned_ids=scanned_ids,
            )
        else:
            state = await sync_to_async(advance_sync_state)(
                state,
                scanned_ids=scanned_ids,
            )

    return SyncStats(
        scanned=scanned,
        matched=matched,
        created=created,
        updated=updated,
        skipped=skipped,
        offset_id=offset_id,
        min_id=min_id,
        oldest_synced_message_id=state.oldest_synced_message_id,
        newest_synced_message_id=state.newest_synced_message_id,
        history_complete=state.history_complete,
    )
