from django.contrib import admin

from apps.categories.models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order", "updated_at")
    list_editable = ("sort_order",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug")
