from django.db import migrations


DEFAULT_CATEGORIES = [
    ("Aqida", "aqida", "Croyance et fondements de la foi", 10),
    ("Fiqh", "fiqh", "Jurisprudence islamique", 20),
    ("Tafsir", "tafsir", "Exégèse du Coran", 30),
    ("Hadith", "hadith", "Science du hadith", 40),
    ("Sira", "sira", "Biographie du Prophète ﷺ", 50),
    ("Autre", "autre", "Autres enseignements", 100),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for name, slug, description, sort_order in DEFAULT_CATEGORIES:
        Category.objects.update_or_create(
            slug=slug,
            defaults={
                "name": name,
                "description": description,
                "sort_order": sort_order,
            },
        )


def unseed_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    Category.objects.filter(slug__in=[slug for _, slug, _, _ in DEFAULT_CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("categories", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]
