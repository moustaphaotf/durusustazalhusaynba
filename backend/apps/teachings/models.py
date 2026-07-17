from django.db import models


class Teaching(models.Model):
    class MediaType(models.TextChoices):
        AUDIO = "audio", "Audio"
        VOICE = "voice", "Voice"
        DOCUMENT = "document", "Document"

    telegram_message_id = models.BigIntegerField()
    telegram_channel_id = models.BigIntegerField()
    title_ar = models.CharField(max_length=500, blank=True)
    title_fr = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    media_type = models.CharField(
        max_length=20,
        choices=MediaType.choices,
        blank=True,
    )
    telegram_file_id = models.CharField(max_length=255, blank=True)
    file_name = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    local_path = models.CharField(max_length=500, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="teachings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-published_at", "-telegram_message_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["telegram_channel_id", "telegram_message_id"],
                name="uniq_teaching_channel_message",
            ),
        ]
        indexes = [
            models.Index(fields=["-published_at"]),
            models.Index(fields=["media_type"]),
        ]

    def __str__(self) -> str:
        return self.title_ar or self.title_fr or f"Teaching #{self.telegram_message_id}"
