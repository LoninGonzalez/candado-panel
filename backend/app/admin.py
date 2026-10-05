from django.contrib import admin

from .models import Aplicacion, Comando, Dispositivo, Politica

admin.site.register(Politica)
admin.site.register(Dispositivo)
admin.site.register(Comando)
admin.site.register(Aplicacion)
admin.site.site_header = "Candado — Administración"
