from django.db import migrations, models


def delete_voice_teachings(apps, schema_editor):
    Teaching = apps.get_model("teachings", "Teaching")
    Teaching.objects.filter(media_type="voice").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("teachings", "0008_add_force_redownload"),
    ]

    operations = [
        migrations.RunPython(
            delete_voice_teachings,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="teaching",
            name="media_type",
            field=models.CharField(
                blank=True,
                choices=[("audio", "Audio"), ("document", "Document")],
                max_length=20,
            ),
        ),
    ]
