from django.contrib import admin
from django.utils import timezone

from apps.teachings.models import Teaching


@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title_ar",
        "title_fr",
        "media_type",
        "download_status",
        "category",
        "published_at",
        "telegram_message_id",
    )
    list_filter = ("media_type", "download_status", "category")
    search_fields = (
        "title_ar",
        "title_fr",
        "description",
        "file_name",
        "telegram_message_id",
        "storage_key",
    )
    raw_id_fields = ("category",)
    readonly_fields = (
        "created_at",
        "updated_at",
        "downloaded_at",
        "storage_key",
        "download_error",
    )
    date_hierarchy = "published_at"
    actions = ("requeue_download",)

    @admin.action(description="Remettre en file de téléchargement (R2)")
    def requeue_download(self, request, queryset):
        """Reset download state so the worker re-fetches from Telegram and re-uploads to R2."""
        updated = queryset.update(
            download_status=Teaching.DownloadStatus.PENDING,
            download_error="",
            storage_key="",
            downloaded_at=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} enseignement(s) remis en pending — le worker les reprendra.",
        )
