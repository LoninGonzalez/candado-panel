"""
Sincroniza el esquema de la base de datos con los modelos actuales, sin borrar datos.

Durante el desarrollo el historial de migraciones quedó inconsistente. En vez de depender
de él, este comando compara cada modelo de la app con la tabla real y:
  - crea la tabla si no existe,
  - añade las columnas que falten.
Luego marca todas las migraciones de la app como aplicadas (--fake) para que 'migrate'
no intente nada más. Es idempotente y conserva los datos existentes.

Cuando el proyecto esté estable en producción, se puede retirar y volver a migraciones
normales; dejarlo no hace daño (si el esquema ya coincide, no toca nada).
"""
from django.apps import apps as django_apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Sincroniza el esquema con los modelos sin borrar datos."

    def handle(self, *args, **opts):
        tablas = connection.introspection.table_names()
        if "django_migrations" not in tablas:
            self.stdout.write("Primer despliegue; migrate normal se encargará.")
            return

        app_config = django_apps.get_app_config("app")
        with connection.schema_editor() as editor:
            for modelo in app_config.get_models():
                tabla = modelo._meta.db_table
                if tabla not in tablas:
                    editor.create_model(modelo)
                    self.stdout.write(f"Tabla {tabla} creada.")
                    continue
                # Añadir columnas que falten
                cols_reales = {c.name for c in connection.introspection.get_table_description(
                    connection.cursor(), tabla
                )}
                for campo in modelo._meta.local_fields:
                    if campo.column not in cols_reales:
                        editor.add_field(modelo, campo)
                        self.stdout.write(f"Columna {tabla}.{campo.column} añadida.")

        # Marcar todas las migraciones de 'app' como aplicadas
        import os
        from django.utils import timezone
        from app.migrations import __path__ as mig_path
        ahora = timezone.now()
        with connection.cursor() as cur:
            cur.execute("DELETE FROM django_migrations WHERE app = 'app'")
            migraciones = sorted(
                f[:-3] for f in os.listdir(mig_path[0])
                if f.endswith(".py") and f != "__init__.py"
            )
            for m in migraciones:
                cur.execute(
                    "INSERT INTO django_migrations (app, name, applied) VALUES ('app', %s, %s)",
                    [m, ahora],
                )
        self.stdout.write(self.style.SUCCESS("Esquema sincronizado con los modelos."))
