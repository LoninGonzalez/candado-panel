import re

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Aplicacion, Comando, Dispositivo, Politica

PAQUETE_RE = re.compile(r"^[a-zA-Z][\w]*(\.[a-zA-Z][\w]*)+$")

RESTRICCIONES = [
    ("bloquear_reset", "Impedir restablecer de fábrica", True),
    ("bloquear_modo_seguro", "Impedir modo seguro", True),
    ("bloquear_instalar", "Impedir instalar apps", True),
    ("bloquear_desinstalar", "Impedir desinstalar apps", True),
    ("bloquear_control_apps", "Impedir forzar detención de apps", True),
    ("bloquear_redes_moviles", "Bloquear datos móviles/APN", True),
    ("bloquear_roaming", "Desactivar roaming", True),
    ("bloquear_hotspot", "Impedir hotspot", True),
    ("bloquear_vpn", "Impedir configurar VPN", True),
    ("bloquear_usb", "Bloquear archivos por USB", True),
    ("bloquear_wifi", "Impedir cambiar Wi-Fi", False),
    ("bloquear_depuracion", "Bloquear opciones de desarrollador", False),
]


def entrar(request):
    if request.method == "POST":
        u = authenticate(request, username=request.POST.get("usuario"),
                         password=request.POST.get("clave"))
        if u:
            login(request, u)
            return redirect("inicio")
        messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "entrar.html")


def salir(request):
    logout(request)
    return redirect("entrar")


@login_required
def inicio(request):
    disp = list(Dispositivo.objects.select_related("politica"))
    en_linea = sum(1 for d in disp if d.en_linea)
    desactualizados = sum(1 for d in disp if not d.al_dia)
    return render(request, "dispositivos.html", {
        "seccion": "disp",
        "dispositivos": disp,
        "en_linea": en_linea,
        "total": len(disp),
        "desactualizados": desactualizados,
        "politicas": Politica.objects.all(),
    })


@login_required
def dispositivo(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    return render(request, "dispositivo.html", {
        "seccion": "disp",
        "d": d,
        "politicas": Politica.objects.all(),
        "apps": Aplicacion.objects.all(),
        "comandos": d.comandos.all()[:20],
    })


@login_required
@require_POST
def dispositivo_alias(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    d.alias = request.POST.get("alias", "").strip()
    d.save(update_fields=["alias"])
    messages.success(request, "Nombre actualizado.")
    return redirect("dispositivo", pk=pk)


@login_required
@require_POST
def dispositivo_politica(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    pol = Politica.objects.filter(pk=request.POST.get("politica")).first()
    d.politica = pol
    d.version_aplicada = None  # fuerza reenvío de política en el próximo checkin
    d.save(update_fields=["politica", "version_aplicada"])
    messages.success(request, "Política asignada. El equipo la aplicará en el próximo sondeo.")
    return redirect("dispositivo", pk=pk)


@login_required
@require_POST
def comando(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    tipo = request.POST.get("tipo")
    datos = {}
    if tipo == Comando.Tipo.INSTALAR:
        app = get_object_or_404(Aplicacion, pk=request.POST.get("app"))
        datos = {"url": app.url, "paquete": app.paquete, "nombre": app.nombre}
    elif tipo == Comando.Tipo.DESINSTALAR:
        datos = {"paquete": request.POST.get("paquete", "")}
    Comando.objects.create(dispositivo=d, tipo=tipo, datos=datos)
    messages.success(request, "Comando encolado. Se enviará en el próximo sondeo del equipo.")
    return redirect("dispositivo", pk=pk)


# -------- Políticas --------

@login_required
def politicas(request):
    pols = Politica.objects.annotate(n=Count("dispositivo"))
    return render(request, "politicas.html", {"politicas": pols, "seccion": "pol"})


@login_required
def politica_editar(request, pk=None):
    pol = get_object_or_404(Politica, pk=pk) if pk else None

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        clave = request.POST.get("clave", "").strip() or _slug(nombre)
        kiosco = request.POST.get("kiosco") == "on"

        # Apps: paquetes separados por línea, con nombre opcional "paquete | Nombre"
        apps = []
        for linea in request.POST.get("apps", "").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            partes = [p.strip() for p in linea.split("|")]
            paquete = partes[0]
            if not PAQUETE_RE.match(paquete):
                messages.error(request, f"Paquete no válido: {paquete}")
                continue
            apps.append({
                "paquete": paquete,
                "nombre": partes[1] if len(partes) > 1 else paquete,
                "datos": True,
            })

        restricciones = {c: (request.POST.get(f"r_{c}") == "on") for c, _, _ in RESTRICCIONES}

        if pol is None:
            pol = Politica(clave=clave)
        pol.nombre = nombre
        pol.kiosco = kiosco
        pol.apps = apps
        pol.restricciones = restricciones
        pol.version = (pol.version + 1) if pol.pk else 1
        pol.save()
        messages.success(request, "Política guardada. Los equipos la recibirán en su próximo sondeo.")
        return redirect("politicas")

    # Preparar datos para el formulario
    apps_texto = ""
    valores_restr = {c: d for c, _, d in RESTRICCIONES}
    if pol:
        apps_texto = "\n".join(
            f"{a['paquete']} | {a.get('nombre', a['paquete'])}" for a in pol.apps
        )
        valores_restr = {c: pol.restricciones.get(c, d) for c, _, d in RESTRICCIONES}

    return render(request, "politica_editar.html", {
        "seccion": "pol",
        "pol": pol,
        "apps_texto": apps_texto,
        "restricciones": [(c, t, valores_restr.get(c, d)) for c, t, d in RESTRICCIONES],
    })


def _slug(texto):
    import unicodedata
    t = unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
    return t[:60] or "politica"


# -------- Aplicaciones --------

@login_required
def aplicaciones(request):
    if request.method == "POST":
        Aplicacion.objects.create(
            nombre=request.POST.get("nombre", "").strip(),
            paquete=request.POST.get("paquete", "").strip(),
            url=request.POST.get("url", "").strip(),
            notas=request.POST.get("notas", "").strip(),
        )
        messages.success(request, "Aplicación agregada al catálogo.")
        return redirect("aplicaciones")
    return render(request, "aplicaciones.html", {"apps": Aplicacion.objects.all(), "seccion": "app"})


@login_required
@require_POST
def aplicacion_borrar(request, pk):
    get_object_or_404(Aplicacion, pk=pk).delete()
    return redirect("aplicaciones")
