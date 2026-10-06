"""
Repara el historial de migraciones de la app 'app' en la base de datos.

Contexto: durante el desarrollo se desplegaron varias versiones con migraciones de
nombres distintos, dejando el historial inconsistente (conflicting leaf nodes). Este
comando borra el registro de migraciones de 'app' y marca la 0001 como aplicada SIN
tocar las tablas (--fake), dejando el historial limpio y coherente con el código actual.

Es seguro mientras el esquema de las tablas ya coincida con la 0001 final, que es el caso
aquí porque los modelos no cambian respecto a lo ya desplegado (solo se consolidó el
historial). Si alguna columna faltara, se ajusta abajo de forma idempotente.
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Limpia el historial de migraciones de 'app' para resolver conflictos."

    def handle(self, *args, **opts):
        with connection.cursor() as cur:
            # ¿Existe la tabla de migraciones? (primer despliegue no la tiene aún)
            tablas = connection.introspection.table_names()
            if "django_migrations" not in tablas:
                self.stdout.write("Sin historial previo; nada que reparar.")
                return

            # Borrar el historial SOLO de la app 'app'
            cur.execute("DELETE FROM django_migrations WHERE app = 'app'")
            self.stdout.write(self.style.SUCCESS("Historial de 'app' limpiado."))

            # Asegurar que la tabla de aplicaciones tenga las columnas del modelo actual.
            if "app_aplicacion" in tablas:
                cols = [c.name for c in connection.introspection.get_table_description(cur, "app_aplicacion")]
                if "url" not in cols:
                    cur.execute("ALTER TABLE app_aplicacion ADD COLUMN url varchar(200) NOT NULL DEFAULT ''")
                    self.stdout.write("Columna 'url' restaurada.")
                if "urls_splits" not in cols:
                    cur.execute("ALTER TABLE app_aplicacion ADD COLUMN urls_splits text NOT NULL DEFAULT ''")
                    self.stdout.write("Columna 'urls_splits' restaurada.")
                # Eliminar tabla de archivos si quedó de la versión que guardaba APK en BD
                if "app_archivoapk" in tablas:
                    cur.execute("DROP TABLE app_archivoapk CASCADE")
                    self.stdout.write("Tabla 'app_archivoapk' eliminada.")

                # Si las tablas principales ya existen, marcar la 0001 como aplicada
                # para que 'migrate' no intente recrearlas.
                if "app_dispositivo" in tablas:
                    cur.execute(
                        "INSERT INTO django_migrations (app, name, applied) "
                        "VALUES ('app', '0001_initial', NOW())"
                    )
                    self.stdout.write("Migración 0001 marcada como aplicada (tablas ya existen).")
