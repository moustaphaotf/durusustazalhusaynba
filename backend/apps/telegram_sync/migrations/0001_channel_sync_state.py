from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ChannelSyncState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("channel_id", models.BigIntegerField(unique=True)),
                (
                    "newest_synced_message_id",
                    models.BigIntegerField(blank=True, null=True),
                ),
                (
                    "oldest_synced_message_id",
                    models.BigIntegerField(blank=True, null=True),
                ),
                ("history_complete", models.BooleanField(default=False)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Channel sync state",
                "verbose_name_plural": "Channel sync states",
            },
        ),
    ]
