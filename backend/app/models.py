import secrets

from django.db import models
from django.utils import timezone


def token_nuevo():
    return secrets.token_urlsafe(24)


class Politica(models.Model):
    class Modo(models.TextChoices):
        LANZADOR = "lanzador", "Pantalla con apps permitidas"
        APP_UNICA = "app_unica", "Una sola app fija"

    nombre = models.CharField(max_length=120)
    clave = models.SlugField(max_length=60, unique=True)
    kiosco = models.BooleanField(default=False)
    # [{"paquete": "...", "nombre": "...", "datos": true}]
    apps = models.JSONField(default=list, blank=True)
    # {"bloquear_reset": true, ...}
    restricciones = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def como_agente(self):
        """JSON en el formato que espera la app Android."""
        return {
            "version": self.version,
            "kiosco": self.kiosco,
            "apps": self.apps,
            "restricciones": self.restricciones,
        }


class Dispositivo(models.Model):
    # android_id que envía el teléfono; lo identifica de forma estable
    uid = models.CharField(max_length=80, unique=True)
    alias = models.CharField(max_length=100, blank=True)
    politica = models.ForeignKey(Politica, null=True, blank=True, on_delete=models.SET_NULL)
    modelo = models.CharField(max_length=100, blank=True)
    marca = models.CharField(max_length=80, blank=True)
    android = models.CharField(max_length=20, blank=True)
    app_version = models.CharField(max_length=20, blank=True)
    bateria = models.IntegerField(null=True, blank=True)
    kiosco_activo = models.BooleanField(null=True)
    version_aplicada = models.PositiveIntegerField(null=True, blank=True)
    visto = models.DateTimeField(null=True, blank=True)
    inscrito = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["alias", "modelo"]

    def __str__(self):
        return self.alias or f"{self.marca} {self.modelo}".strip() or self.uid

    @property
    def en_linea(self):
        if not self.visto:
            return False
        return (timezone.now() - self.visto).total_seconds() < 600  # 10 min

    @property
    def al_dia(self):
        return bool(self.politica and self.version_aplicada == self.politica.version)


class Comando(models.Model):
    class Tipo(models.TextChoices):
        BLOQUEAR = "bloquear", "Bloquear pantalla"
        REINICIAR = "reiniciar", "Reiniciar equipo"
        INSTALAR = "instalar", "Instalar aplicación"
        DESINSTALAR = "desinstalar", "Desinstalar aplicación"
        SINCRONIZAR = "sincronizar", "Forzar sincronización"

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        ENVIADO = "enviado", "Enviado al equipo"
        OK = "ok", "Completado"
        ERROR = "error", "Error"

    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name="comandos")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    # Para instalar: {"url": "...", "paquete": "..."}; desinstalar: {"paquete": "..."}
    datos = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PENDIENTE)
    resultado = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    entregado = models.DateTimeField(null=True, blank=True)
    completado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.get_tipo_display()} → {self.dispositivo}"


class Aplicacion(models.Model):
    """Catálogo de apps instalables. Los APK se guardan en la BD (modelo ArchivoApk)."""

    nombre = models.CharField(max_length=120)
    paquete = models.CharField(max_length=150)
    notas = models.CharField(max_length=200, blank=True)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.paquete})"

    def lista_urls(self, base_url, token=""):
        """URLs internas para que el teléfono descargue cada APK. base primero."""
        sufijo = f"?token={token}" if token else ""
        return [base_url.rstrip("/") + a.ruta_descarga() + sufijo for a in self.archivos.all()]

    @property
    def es_dividida(self):
        return self.archivos.count() > 1

    @property
    def total_mb(self):
        total = sum(a.tamano for a in self.archivos.all())
        return round(total / 1048576, 1)


class ArchivoApk(models.Model):
    """Un APK (base o split) guardado como bytes en la base de datos."""

    aplicacion = models.ForeignKey(Aplicacion, on_delete=models.CASCADE, related_name="archivos")
    nombre = models.CharField(max_length=160)  # p. ej. base.apk
    contenido = models.BinaryField()
    tamano = models.PositiveIntegerField(default=0)
    es_base = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-es_base", "orden", "nombre"]

    def __str__(self):
        return self.nombre

    def ruta_descarga(self):
        return f"/apk/{self.id}/{self.nombre}"
