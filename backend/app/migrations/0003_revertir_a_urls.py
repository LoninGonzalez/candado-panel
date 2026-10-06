from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("app", "0002_aplicacion_urls_splits_alter_aplicacion_url")]

    operations = [
        migrations.DeleteModel(name="ArchivoApk"),
        migrations.AddField(
            model_name="aplicacion",
            name="url",
            field=models.URLField(default="", help_text="URL del APK base (https)"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="aplicacion",
            name="urls_splits",
            field=models.TextField(blank=True, help_text="URLs de los splits, una por línea."),
        ),
    ]
