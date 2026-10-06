from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea el usuario admin inicial si no existe."

    def handle(self, *args, **opts):
        u = settings.ADMIN_USER
        if not User.objects.filter(username=u).exists():
            User.objects.create_superuser(u, "", settings.ADMIN_PASSWORD)
            self.stdout.write(self.style.SUCCESS(f"Admin '{u}' creado."))
        else:
            self.stdout.write(f"Admin '{u}' ya existe.")
