import re

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AppConocida, Aplicacion, Comando, Dispositivo, Grupo, Politica, VersionApp

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


def _politica_o_none(valor):
    """Devuelve la Política con ese id, o None si el valor está vacío o no existe.
    Evita el error 500 cuando el formulario envía 'Sin política' (valor vacío)."""
    if not valor:
        return None
    return Politica.objects.filter(pk=valor).first()


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
    qs = Dispositivo.objects.select_related("politica").prefetch_related("grupos")
    # Filtro opcional por grupo
    grupo_id = request.GET.get("grupo")
    grupo_sel = None
    if grupo_id:
        grupo_sel = Grupo.objects.filter(pk=grupo_id).first()
        if grupo_sel:
            qs = qs.filter(grupos=grupo_sel)
    disp = list(qs)
    en_linea = sum(1 for d in disp if d.en_linea)
    desactualizados = sum(1 for d in disp if not d.al_dia)
    return render(request, "dispositivos.html", {
        "seccion": "disp",
        "dispositivos": disp,
        "en_linea": en_linea,
        "total": len(disp),
        "desactualizados": desactualizados,
        "politicas": Politica.objects.all(),
        "grupos": Grupo.objects.all(),
        "grupo_sel": grupo_sel,
    })


@login_required
def dispositivo(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    return render(request, "dispositivo.html", {
        "seccion": "disp",
        "d": d,
        "politicas": Politica.objects.all(),
        "grupos": Grupo.objects.all(),
        "grupos_del_equipo": set(d.grupos.values_list("pk", flat=True)),
        "politica_efectiva": d.politica_efectiva(),
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
    pol = _politica_o_none(request.POST.get("politica"))
    d.politica = pol
    d.version_aplicada = None  # fuerza reenvío de política en el próximo checkin
    d.save(update_fields=["politica", "version_aplicada"])
    messages.success(request, "Política asignada. El equipo la aplicará en el próximo sondeo.")
    return redirect("dispositivo", pk=pk)


@login_required
@require_POST
def dispositivo_grupos(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    ids = request.POST.getlist("grupos")
    d.grupos.set(Grupo.objects.filter(pk__in=ids))
    d.version_aplicada = None  # por si cambió la política heredada
    d.save(update_fields=["version_aplicada"])
    messages.success(request, "Grupos actualizados.")
    return redirect("dispositivo", pk=pk)


# -------- Grupos --------

@login_required
def grupos(request):
    gs = (Grupo.objects.select_related("politica")
          .prefetch_related("dispositivos__politica")
          .annotate(n=Count("dispositivos")))
    return render(request, "grupos.html", {"seccion": "grupo", "grupos": gs})


@login_required
def grupo_editar(request, pk=None):
    g = get_object_or_404(Grupo, pk=pk) if pk else None
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        if not nombre:
            messages.error(request, "El grupo necesita un nombre.")
            return redirect("grupos")
        pol = _politica_o_none(request.POST.get("politica"))
        try:
            orden = max(0, int(request.POST.get("orden") or 0))
        except ValueError:
            orden = 0
        if g is None:
            g = Grupo()
        g.nombre = nombre
        g.descripcion = request.POST.get("descripcion", "").strip()
        g.politica = pol
        g.orden = orden
        g.save()
        # Equipos que pertenecen al grupo (casillas marcadas)
        antes = set(g.dispositivos.values_list("pk", flat=True))
        seleccionados = Dispositivo.objects.filter(pk__in=request.POST.getlist("dispositivos"))
        g.dispositivos.set(seleccionados)
        despues = set(seleccionados.values_list("pk", flat=True))
        # Forzar re-sincronización: miembros actuales (su política pudo cambiar) y los que salieron
        afectados = despues | (antes - despues)
        Dispositivo.objects.filter(pk__in=afectados).update(version_aplicada=None)
        messages.success(request, "Grupo guardado.")
        return redirect("grupos")
    return render(request, "grupo_editar.html", {
        "seccion": "grupo", "g": g, "politicas": Politica.objects.all(),
        "dispositivos": Dispositivo.objects.all(),
        "en_grupo": set(g.dispositivos.values_list("pk", flat=True)) if g else set(),
    })


@login_required
@require_POST
def grupo_borrar(request, pk):
    g = get_object_or_404(Grupo, pk=pk)
    g.dispositivos.update(version_aplicada=None)  # recalcular política al perder el grupo
    g.delete()
    messages.success(request, "Grupo eliminado.")
    return redirect("grupos")


@login_required
@require_POST
def comando(request, pk):
    d = get_object_or_404(Dispositivo, pk=pk)
    tipo = request.POST.get("tipo")
    datos = {}
    if tipo == Comando.Tipo.INSTALAR:
        app = Aplicacion.objects.filter(pk=request.POST.get("app") or 0).first()
        if not app:
            messages.error(request, "Elige una aplicación para instalar.")
            return redirect("dispositivo", pk=pk)
        datos = {
            "urls": app.lista_urls(),   # lista: base + splits
            "paquete": app.paquete,
            "nombre": app.nombre,
        }
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
        try:
            tope_total = max(0, int(request.POST.get("tope_total_mb") or 0))
        except ValueError:
            tope_total = 0

        # Apps elegidas en el catálogo (checkbox "permitida").
        apps = []
        vistos = set()
        for pkg in request.POST.getlist("app_sel"):
            pkg = pkg.strip()
            if not pkg or pkg in vistos or not PAQUETE_RE.match(pkg):
                continue
            vistos.add(pkg)
            nombre_app = request.POST.get(f"nombre_{pkg}", "").strip() or pkg
            apps.append({
                "paquete": pkg,
                "nombre": nombre_app,
                "datos": request.POST.get(f"datos_{pkg}") == "on",
                "tope_mensual_mb": _entero(request.POST.get(f"tope_{pkg}")),
            })

        # Apps agregadas a mano (paquetes que no están en el catálogo todavía).
        # Formato por línea: paquete | Nombre | tope_MB
        for linea in request.POST.get("apps_manual", "").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            partes = [p.strip() for p in linea.split("|")]
            paquete = partes[0]
            if not PAQUETE_RE.match(paquete):
                messages.error(request, f"Paquete no válido: {paquete}")
                continue
            if paquete in vistos:
                continue
            vistos.add(paquete)
            nombre_app = partes[1] if len(partes) > 1 and partes[1] else paquete
            tope_app = _entero(partes[2]) if len(partes) > 2 else 0
            apps.append({
                "paquete": paquete,
                "nombre": nombre_app,
                "datos": True,
                "tope_mensual_mb": tope_app,
            })
            # Que quede en el catálogo para la próxima vez
            AppConocida.objects.update_or_create(
                paquete=paquete, defaults={"nombre": nombre_app, "origen": "equipo"},
            )

        restricciones = {c: (request.POST.get(f"r_{c}") == "on") for c, _, _ in RESTRICCIONES}

        if pol is None:
            pol = Politica(clave=clave)
        pol.nombre = nombre
        pol.kiosco = kiosco
        pol.tope_total_mb = tope_total
        pol.apps = apps
        pol.restricciones = restricciones
        pol.version = (pol.version + 1) if pol.pk else 1
        pol.save()
        messages.success(request, "Política guardada. Los equipos la recibirán en su próximo sondeo.")
        return redirect("politicas")

    # Preparar datos para el formulario
    valores_restr = {c: d for c, _, d in RESTRICCIONES}
    if pol:
        valores_restr = {c: pol.restricciones.get(c, d) for c, _, d in RESTRICCIONES}

    # Apps ya permitidas en esta política, por paquete
    seleccionadas = {a["paquete"]: a for a in (pol.apps if pol else [])}

    # Catálogo: apps conocidas (base + reportadas por equipos) + las ya permitidas
    # que todavía no estén en el catálogo.
    catalogo = list(AppConocida.objects.all())
    en_catalogo = {a.paquete for a in catalogo}
    filas = []
    for app in catalogo:
        sel = seleccionadas.get(app.paquete)
        filas.append({
            "paquete": app.paquete,
            "nombre": app.nombre,
            "permitida": sel is not None,
            "datos": sel.get("datos", True) if sel else True,
            "tope": sel.get("tope_mensual_mb", 0) if sel else 0,
            "origen": app.origen,
            "icono": app.icono,
        })
    for pkg, a in seleccionadas.items():
        if pkg not in en_catalogo:
            filas.append({
                "paquete": pkg,
                "nombre": a.get("nombre", pkg),
                "permitida": True,
                "datos": a.get("datos", True),
                "tope": a.get("tope_mensual_mb", 0),
                "origen": "manual",
                "icono": "",
            })
    # Permitidas primero, luego alfabético
    filas.sort(key=lambda f: (not f["permitida"], f["nombre"].lower()))

    return render(request, "politica_editar.html", {
        "seccion": "pol",
        "pol": pol,
        "filas": filas,
        "n_permitidas": sum(1 for f in filas if f["permitida"]),
        "restricciones": [(c, t, valores_restr.get(c, d)) for c, t, d in RESTRICCIONES],
    })


def _entero(valor):
    """Entero >= 0 a partir de un texto; 0 si está vacío o no es número."""
    try:
        return max(0, int(valor))
    except (TypeError, ValueError):
        return 0


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
            urls_splits=request.POST.get("urls_splits", "").strip(),
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


# -------- Auto-actualización de la app --------

@login_required
def actualizacion(request):
    if request.method == "POST":
        try:
            vc = int(request.POST.get("version_code") or 0)
        except ValueError:
            vc = 0
        vn = request.POST.get("version_name", "").strip()
        url = request.POST.get("url", "").strip()
        if vc <= 0 or not vn or not url:
            messages.error(request, "Completa versionCode, versionName y la URL del APK.")
            return redirect("actualizacion")
        VersionApp.objects.create(
            version_code=vc, version_name=vn, url=url,
            notas=request.POST.get("notas", "").strip(),
            activa=True,
        )
        messages.success(request, f"Versión {vn} publicada. Los equipos se actualizarán en su próximo sondeo.")
        return redirect("actualizacion")

    versiones = VersionApp.objects.all()[:20]
    equipos = Dispositivo.objects.all()
    actual = VersionApp.actual()
    # Cuántos equipos están ya en la versión disponible (comparando versionName)
    al_dia = sum(1 for e in equipos if actual and e.app_version == actual.version_name)
    return render(request, "actualizacion.html", {
        "seccion": "upd",
        "versiones": versiones,
        "actual": actual,
        "total_equipos": equipos.count(),
        "al_dia": al_dia,
    })


@login_required
@require_POST
def actualizacion_alternar(request, pk):
    v = get_object_or_404(VersionApp, pk=pk)
    v.activa = not v.activa
    v.save(update_fields=["activa"])
    messages.success(request, "Estado de la versión actualizado.")
    return redirect("actualizacion")
