from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("teachings", "0007_add_download_requested_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="teaching",
            name="force_redownload",
            field=models.BooleanField(default=False),
        ),
    ]
