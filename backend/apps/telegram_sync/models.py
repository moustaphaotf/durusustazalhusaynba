from django.db import models


class ChannelSyncState(models.Model):
    """Cursor for sequential channel history sync (newest → oldest)."""

    channel_id = models.BigIntegerField(unique=True)
    newest_synced_message_id = models.BigIntegerField(null=True, blank=True)
    oldest_synced_message_id = models.BigIntegerField(null=True, blank=True)
    history_complete = models.BooleanField(default=False)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Channel sync state"
        verbose_name_plural = "Channel sync states"

    def __str__(self) -> str:
        return (
            f"channel={self.channel_id} "
            f"oldest={self.oldest_synced_message_id} "
            f"newest={self.newest_synced_message_id}"
        )
