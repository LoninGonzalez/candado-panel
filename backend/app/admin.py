from django.contrib import admin

from .models import Aplicacion, Comando, Dispositivo, Grupo, Politica, VersionApp

admin.site.register(Politica)
admin.site.register(Grupo)
admin.site.register(Dispositivo)
admin.site.register(Comando)
admin.site.register(Aplicacion)
admin.site.register(VersionApp)
admin.site.site_header = "Candado — Administración"
