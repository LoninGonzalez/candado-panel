"""Endpoints que consumen los teléfonos. Autenticación por token compartido."""
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Comando, Dispositivo, Politica


def token_valido(request):
    enviado = request.headers.get("X-Token", "")
    return enviado and enviado == settings.AGENTE_TOKEN


def no_autorizado():
    return Response({"detalle": "Token inválido."}, status=401)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def checkin(request):
    """
    El teléfono reporta su estado y recibe: su política (si cambió) y comandos pendientes.
    Cuerpo esperado:
    {
      "uid": "...", "modelo": "...", "marca": "...", "android": "13",
      "app_version": "0.3.5", "bateria": 80, "kiosco_activo": true,
      "version_aplicada": 3
    }
    """
    if not token_valido(request):
        return no_autorizado()

    d = request.data
    uid = d.get("uid")
    if not uid:
        return Response({"detalle": "Falta uid."}, status=400)

    disp, creado = Dispositivo.objects.get_or_create(uid=uid)
    disp.modelo = d.get("modelo", disp.modelo)
    disp.marca = d.get("marca", disp.marca)
    disp.android = d.get("android", disp.android)
    disp.app_version = d.get("app_version", disp.app_version)
    disp.bateria = d.get("bateria", disp.bateria)
    disp.kiosco_activo = d.get("kiosco_activo", disp.kiosco_activo)
    disp.version_aplicada = d.get("version_aplicada", disp.version_aplicada)
    disp.visto = timezone.now()

    # Consumo de datos reportado
    consumo = d.get("consumo")
    if isinstance(consumo, dict):
        disp.consumo_total_mb = consumo.get("total_mb")
        disp.consumo_por_app = consumo.get("por_app", {})
        disp.tope_superado = bool(consumo.get("tope_superado"))

    disp.save()

    # Comandos pendientes
    pendientes = disp.comandos.filter(estado=Comando.Estado.PENDIENTE)
    comandos = []
    for c in pendientes:
        comandos.append({"id": c.id, "tipo": c.tipo, "datos": c.datos})
        c.estado = Comando.Estado.ENVIADO
        c.entregado = timezone.now()
        c.save(update_fields=["estado", "entregado"])

    # Política: se envía solo si el equipo no está al día
    politica = None
    if disp.politica and disp.version_aplicada != disp.politica.version:
        politica = disp.politica.como_agente()

    return Response({
        "politica": politica,
        "comandos": comandos,
        "intervalo_seg": 120,
    })


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def resultado_comando(request, comando_id):
    """El teléfono informa si un comando se completó o falló."""
    if not token_valido(request):
        return no_autorizado()
    try:
        c = Comando.objects.get(id=comando_id)
    except Comando.DoesNotExist:
        return Response({"detalle": "Comando no existe."}, status=404)

    ok = request.data.get("ok", False)
    c.estado = Comando.Estado.OK if ok else Comando.Estado.ERROR
    c.resultado = request.data.get("resultado", "")[:2000]
    c.completado = timezone.now()
    c.save(update_fields=["estado", "resultado", "completado"])
    return Response({"detalle": "Recibido."})
