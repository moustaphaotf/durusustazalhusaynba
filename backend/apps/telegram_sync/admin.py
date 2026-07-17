from django.contrib import admin

from apps.telegram_sync.models import ChannelSyncState


@admin.register(ChannelSyncState)
class ChannelSyncStateAdmin(admin.ModelAdmin):
    list_display = (
        "channel_id",
        "oldest_synced_message_id",
        "newest_synced_message_id",
        "history_complete",
        "last_synced_at",
    )
    readonly_fields = ("last_synced_at",)
