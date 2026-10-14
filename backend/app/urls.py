from django.urls import path

from . import api_agente, views

urlpatterns = [
    # Panel web (sesión)
    path("entrar/", views.entrar, name="entrar"),
    path("salir/", views.salir, name="salir"),
    path("", views.inicio, name="inicio"),
    path("dispositivo/<int:pk>/", views.dispositivo, name="dispositivo"),
    path("dispositivo/<int:pk>/alias/", views.dispositivo_alias, name="dispositivo_alias"),
    path("dispositivo/<int:pk>/politica/", views.dispositivo_politica, name="dispositivo_politica"),
    path("dispositivo/<int:pk>/grupos/", views.dispositivo_grupos, name="dispositivo_grupos"),
    path("dispositivo/<int:pk>/comando/", views.comando, name="comando"),
    path("grupos/", views.grupos, name="grupos"),
    path("grupos/nuevo/", views.grupo_editar, name="grupo_nuevo"),
    path("grupos/<int:pk>/", views.grupo_editar, name="grupo_editar"),
    path("grupos/<int:pk>/borrar/", views.grupo_borrar, name="grupo_borrar"),
    path("politicas/", views.politicas, name="politicas"),
    path("politicas/nueva/", views.politica_editar, name="politica_nueva"),
    path("politicas/<int:pk>/", views.politica_editar, name="politica_editar"),
    path("aplicaciones/", views.aplicaciones, name="aplicaciones"),
    path("aplicaciones/<int:pk>/borrar/", views.aplicacion_borrar, name="aplicacion_borrar"),
    path("actualizacion/", views.actualizacion, name="actualizacion"),
    path("actualizacion/<int:pk>/alternar/", views.actualizacion_alternar, name="actualizacion_alternar"),
    path("tile/<int:z>/<int:x>/<int:y>.png", views.tile, name="tile"),

    # API para teléfonos (token)
    path("api/checkin/", api_agente.checkin, name="checkin"),
    path("api/comando/<int:comando_id>/resultado/", api_agente.resultado_comando, name="resultado_comando"),
]
