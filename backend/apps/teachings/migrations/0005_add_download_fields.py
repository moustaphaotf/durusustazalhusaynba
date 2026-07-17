from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teachings", "0004_add_telegram_message_url"),
    ]

    operations = [
        migrations.AddField(
            model_name="teaching",
            name="storage_key",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="teaching",
            name="download_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("processing", "Processing"),
                    ("ready", "Ready"),
                    ("failed", "Failed"),
                    ("skipped", "Skipped"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="teaching",
            name="download_error",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="teaching",
            name="downloaded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="teaching",
            index=models.Index(
                fields=["download_status"],
                name="teachings_t_downloa_idx",
            ),
        ),
    ]
