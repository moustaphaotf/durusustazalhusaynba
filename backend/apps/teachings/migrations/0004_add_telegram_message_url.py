from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("teachings", "0003_rename_title_add_title_fr"),
    ]

    operations = [
        migrations.AddField(
            model_name="teaching",
            name="telegram_message_url",
            field=models.URLField(blank=True, max_length=500),
        ),
    ]
