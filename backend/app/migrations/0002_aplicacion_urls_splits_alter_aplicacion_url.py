# Esta migración ya fue aplicada en producción (creó ArchivoApk).
# La 0003 revierte este cambio hacia el enfoque de URLs.
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("app", "0001_initial")]

    operations = [
        migrations.RemoveField(model_name="aplicacion", name="url"),
        migrations.CreateModel(
            name="ArchivoApk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("nombre", models.CharField(max_length=160)),
                ("contenido", models.BinaryField()),
                ("tamano", models.PositiveIntegerField(default=0)),
                ("es_base", models.BooleanField(default=False)),
                ("orden", models.PositiveIntegerField(default=0)),
                ("aplicacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="archivos", to="app.aplicacion")),
            ],
            options={"ordering": ["-es_base", "orden", "nombre"]},
        ),
    ]
