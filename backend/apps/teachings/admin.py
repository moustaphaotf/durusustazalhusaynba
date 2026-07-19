from django.conf import settings
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from apps.teachings.models import Teaching
from apps.telegram_sync import storage


@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title_ar",
        "title_fr",
        "media_type",
        "download_status",
        "listen_link",
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
        "listen_link",
        "created_at",
        "updated_at",
        "downloaded_at",
        "download_requested_at",
        "force_redownload",
        "storage_key",
        "download_error",
    )
    date_hierarchy = "published_at"
    actions = ("download_now", "reconcile_with_r2", "requeue_download")

    @admin.display(description="Écouter")
    def listen_link(self, obj: Teaching):
        """Open a short-lived R2 URL in a new tab when media is ready."""
        if (
            obj.download_status != Teaching.DownloadStatus.READY
            or not obj.storage_key
        ):
            return "—"

        url = storage.generate_presigned_url(
            obj.storage_key,
            expires_in=settings.R2_PRESIGNED_URL_TTL,
        )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">Écouter</a>',
            url,
        )

    @admin.action(description="Télécharger maintenant (prioritaire)")
    def download_now(self, request, queryset):
        """Prioritize not-yet-ready teachings for background download.

        Already-ready items are left untouched — use « Remettre en file »
        to force a full re-download.
        """
        eligible = queryset.exclude(
            download_status__in=(
                Teaching.DownloadStatus.READY,
                Teaching.DownloadStatus.PROCESSING,
            ),
        )
        updated = eligible.update(
            download_status=Teaching.DownloadStatus.PENDING,
            download_error="",
            download_requested_at=timezone.now(),
            force_redownload=False,
            updated_at=timezone.now(),
        )
        skipped = queryset.count() - updated
        message = (
            f"{updated} enseignement(s) en file prioritaire — "
            "téléchargement en arrière-plan d'ici quelques secondes."
        )
        if skipped:
            message += (
                f" ({skipped} déjà prêts ou en cours, ignoré(s).)"
            )
        self.message_user(request, message)

    @admin.action(description="Réconcilier avec R2")
    def reconcile_with_r2(self, request, queryset):
        """Restore READY from R2, or leave missing objects PENDING.

        This only performs lightweight R2 metadata requests. It never
        downloads media and never marks an item PROCESSING.
        """
        found = 0
        missing = 0
        skipped = 0
        errors = 0
        now = timezone.now()

        for teaching in queryset.iterator():
            if teaching.download_status == Teaching.DownloadStatus.PROCESSING:
                skipped += 1
                continue

            try:
                existing_key = storage.find_existing_teaching_key(
                    channel_id=teaching.telegram_channel_id,
                    message_id=teaching.telegram_message_id,
                    known_key=teaching.storage_key,
                )
            except Exception:  # noqa: BLE001 - one R2 error must not abort the selection
                errors += 1
                continue

            if existing_key:
                Teaching.objects.filter(pk=teaching.pk).update(
                    storage_key=existing_key,
                    download_status=Teaching.DownloadStatus.READY,
                    download_error="",
                    download_requested_at=None,
                    force_redownload=False,
                    updated_at=now,
                )
                found += 1
            else:
                Teaching.objects.filter(pk=teaching.pk).update(
                    storage_key="",
                    download_status=Teaching.DownloadStatus.PENDING,
                    download_error="",
                    download_requested_at=None,
                    force_redownload=False,
                    downloaded_at=None,
                    updated_at=now,
                )
                missing += 1

        summary = (
            f"Réconciliation R2 terminée : {found} trouvé(s) → ready, "
            f"{missing} absent(s) → pending."
        )
        if skipped:
            summary += f" {skipped} en cours ignoré(s)."
        if errors:
            summary += f" {errors} erreur(s) R2, statut inchangé."
        self.message_user(request, summary)

    @admin.action(description="Remettre en file de téléchargement")
    def requeue_download(self, request, queryset):
        """Force a Telegram re-download and R2 overwrite on the next worker pass."""
        updated = queryset.update(
            download_status=Teaching.DownloadStatus.PENDING,
            download_error="",
            storage_key="",
            download_requested_at=None,
            force_redownload=True,
            downloaded_at=None,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            f"{updated} enseignement(s) remis en pending (re-téléchargement forcé).",
        )
