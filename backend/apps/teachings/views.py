from rest_framework import mixins, viewsets

from apps.teachings.models import Teaching
from apps.teachings.serializers import TeachingDetailSerializer, TeachingListSerializer


class TeachingViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Teaching.objects.select_related("category").all()

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
