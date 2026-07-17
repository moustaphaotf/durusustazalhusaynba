from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teachings", "0002_add_local_path"),
    ]

    operations = [
        migrations.RenameField(
            model_name="teaching",
            old_name="title",
            new_name="title_ar",
        ),
        migrations.AddField(
            model_name="teaching",
            name="title_fr",
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
