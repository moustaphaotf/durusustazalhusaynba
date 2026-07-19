from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("teachings", "0006_rename_download_status_index"),
    ]

    operations = [
        migrations.AddField(
            model_name="teaching",
            name="download_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
