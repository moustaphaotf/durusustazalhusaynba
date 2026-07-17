from rest_framework import serializers

from apps.categories.serializers import CategorySerializer
from apps.teachings.models import Teaching


class TeachingListSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Teaching
        fields = (
            "id",
            "telegram_message_id",
            "title_ar",
            "title_fr",
            "media_type",
            "file_name",
            "file_size",
            "published_at",
            "category",
        )


class TeachingDetailSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Teaching
        fields = (
            "id",
            "telegram_message_id",
            "telegram_channel_id",
            "title_ar",
            "title_fr",
            "description",
            "media_type",
            "telegram_file_id",
            "file_name",
            "file_size",
            "local_path",
            "published_at",
            "category",
            "created_at",
            "updated_at",
        )
