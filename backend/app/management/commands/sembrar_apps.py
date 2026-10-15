"""Siembra el catálogo con apps comunes, para que el buscador no esté vacío al inicio."""
from django.core.management.base import BaseCommand

from app.models import AppConocida

COMUNES = [
    ("com.whatsapp", "WhatsApp"),
    ("com.whatsapp.w4b", "WhatsApp Business"),
    ("com.google.android.apps.maps", "Google Maps"),
    ("com.waze", "Waze"),
    ("com.android.chrome", "Chrome"),
    ("com.google.android.gm", "Gmail"),
    ("com.google.android.youtube", "YouTube"),
    ("com.facebook.katana", "Facebook"),
    ("com.facebook.orca", "Messenger"),
    ("com.instagram.android", "Instagram"),
    ("org.telegram.messenger", "Telegram"),
    ("com.google.android.dialer", "Teléfono"),
    ("com.google.android.apps.messaging", "Mensajes"),
    ("com.google.android.contacts", "Contactos"),
    ("com.google.android.calendar", "Calendario"),
    ("com.google.android.GoogleCamera", "Cámara"),
    ("com.android.vending", "Google Play Store"),
    ("com.google.android.apps.photos", "Google Fotos"),
    ("com.google.android.apps.docs", "Google Drive"),
    ("com.microsoft.office.outlook", "Outlook"),
    ("com.ubercab", "Uber"),
    ("com.ubercab.driver", "Uber Driver"),
    ("com.spotify.music", "Spotify"),
    ("com.zoom.videomeetings", "Zoom"),
    ("us.zoom.videomeetings", "Zoom"),
    ("com.alegra.app", "Alegra"),
]


class Command(BaseCommand):
    help = "Siembra el catálogo de apps comunes (no pisa las reportadas por equipos)."

    def handle(self, *args, **opts):
        nuevas = 0
        for paquete, nombre in COMUNES:
            _, creada = AppConocida.objects.get_or_create(
                paquete=paquete, defaults={"nombre": nombre, "origen": "base"},
            )
            if creada:
                nuevas += 1
        self.stdout.write(self.style.SUCCESS(f"Catálogo sembrado: {nuevas} apps nuevas."))
