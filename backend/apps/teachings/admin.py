from django.contrib import admin

from apps.teachings.models import Teaching


@admin.register(Teaching)
class TeachingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "media_type",
        "category",
        "published_at",
        "telegram_message_id",
    )
    list_filter = ("media_type", "category")
    search_fields = ("title", "description", "file_name", "telegram_message_id")
    raw_id_fields = ("category",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "published_at"
