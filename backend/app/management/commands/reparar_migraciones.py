"""
Repara el esquema de la app 'app' para que coincida con las migraciones actuales.

Durante el desarrollo se cambió el modelo varias veces sobre una base ya desplegada,
dejando el historial de migraciones inconsistente y columnas desincronizadas. Como la
app todavía no tiene datos de producción que preservar, la forma más fiable de garantizar
que el esquema coincida con el código es: borrar las tablas de 'app' y su historial de
migraciones, para que 'migrate' las recree limpias desde 0001.

IMPORTANTE: esto BORRA los datos de la app (políticas, equipos, comandos, aplicaciones).
Es aceptable en esta etapa de desarrollo. Cuando el producto tenga datos reales que
conservar, hay que quitar este comando y manejar los cambios de modelo con migraciones
normales.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Recrea el esquema de 'app' desde cero para evitar inconsistencias."

    # Tablas de la app, en orden de borrado (dependientes primero)
    TABLAS = ["app_comando", "app_archivoapk", "app_miembro", "app_evento",
              "app_dispositivo", "app_aplicacion", "app_politica"]

    def handle(self, *args, **opts):
        tablas_existentes = connection.introspection.table_names()
        if "django_migrations" not in tablas_existentes:
            self.stdout.write("Primer despliegue; nada que reparar.")
            return

        with connection.cursor() as cur:
            # ¿El esquema ya está sano? Si app_politica tiene tope_total_mb, no tocar nada.
            if "app_politica" in tablas_existentes:
                cols = [c.name for c in connection.introspection.get_table_description(cur, "app_politica")]
                if "tope_total_mb" in cols:
                    self.stdout.write("Esquema ya actualizado; sin cambios.")
                    return

            # Borrar tablas de la app. CASCADE solo en Postgres (producción).
            cascade = "CASCADE" if connection.vendor == "postgresql" else ""
            for t in self.TABLAS:
                if t in tablas_existentes:
                    cur.execute(f"DROP TABLE IF EXISTS {t} {cascade}")
                    self.stdout.write(f"Tabla {t} eliminada.")

            # Borrar el historial de migraciones de 'app'
            cur.execute("DELETE FROM django_migrations WHERE app = 'app'")
            self.stdout.write(self.style.SUCCESS(
                "Esquema de 'app' limpiado. 'migrate' lo recreará desde 0001."
            ))
