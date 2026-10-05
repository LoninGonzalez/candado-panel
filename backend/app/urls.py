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
    path("dispositivo/<int:pk>/comando/", views.comando, name="comando"),
    path("politicas/", views.politicas, name="politicas"),
    path("politicas/nueva/", views.politica_editar, name="politica_nueva"),
    path("politicas/<int:pk>/", views.politica_editar, name="politica_editar"),
    path("aplicaciones/", views.aplicaciones, name="aplicaciones"),
    path("aplicaciones/<int:pk>/borrar/", views.aplicacion_borrar, name="aplicacion_borrar"),

    # API para teléfonos (token)
    path("api/checkin/", api_agente.checkin, name="checkin"),
    path("api/comando/<int:comando_id>/resultado/", api_agente.resultado_comando, name="resultado_comando"),
]
