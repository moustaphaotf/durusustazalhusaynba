from django.conf import settings
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.teachings.models import Teaching
from apps.teachings.serializers import TeachingDetailSerializer, TeachingListSerializer
from apps.telegram_sync import storage


class TeachingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Teaching.objects.select_related("category").filter(
        download_status=Teaching.DownloadStatus.READY,
    )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return TeachingDetailSerializer
        return TeachingListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category_slug = self.request.query_params.get("category")
        media_type = self.request.query_params.get("media_type")

        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if media_type:
            queryset = queryset.filter(media_type=media_type)

        return queryset

    @action(detail=True, methods=["get"])
    def media(self, request, pk=None):
        teaching = self.get_object()

        if (
            teaching.download_status != Teaching.DownloadStatus.READY
            or not teaching.storage_key
        ):
            return Response(
                {
                    "detail": "Media is not available yet.",
                    "download_status": teaching.download_status,
                },
                status=status.HTTP_409_CONFLICT,
            )

        ttl = settings.R2_PRESIGNED_URL_TTL
        url = storage.generate_presigned_url(teaching.storage_key, expires_in=ttl)
        return Response({"url": url, "expires_in": ttl})
