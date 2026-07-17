from rest_framework import mixins, viewsets

from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer


class CategoryViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = "slug"
