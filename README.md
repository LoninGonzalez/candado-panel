# Candado — Panel web

Panel para administrar la flota de equipos con Candado AppLock: políticas, estado de
los dispositivos, comandos (bloquear, reiniciar, instalar apps) e instalación remota de APKs.

- `backend/` — Django + DRF + Postgres. Panel web (sesión) + API para los teléfonos (token).

## Cómo funciona

- **Panel web**: tú entras con usuario y contraseña, gestionas políticas y equipos.
- **Los teléfonos** hacen *checkin* cada 2 minutos: reportan su estado y reciben su política
  (si cambió) y los comandos pendientes. No hay push; es sondeo, simple y confiable.
- Los teléfonos se autentican con un **token compartido** (`AGENTE_TOKEN`), que también va
  configurado en la app. El panel se protege con login de usuario.

## Desplegar gratis en Render (recomendado para empezar)

El proyecto ya trae `render.yaml`, que le dice a Render cómo montar todo.

1. Sube este proyecto a un repositorio en **GitHub** (gratis).
2. Entra a https://render.com y crea una cuenta (puedes usar tu GitHub).
3. **New → Blueprint**, elige tu repositorio. Render lee `render.yaml` y propone
   crear el servicio web + la base de datos Postgres. Acepta.
4. Te pedirá definir `ADMIN_PASSWORD` (la contraseña de tu panel). Ponla.
5. Render construye y despliega. En unos minutos tendrás una URL como
   `https://candado-panel.onrender.com`, con HTTPS ya incluido.
6. Entra con usuario `admin` y la contraseña que pusiste.

**El token de los teléfonos**: Render lo genera solo (`AGENTE_TOKEN`). Para verlo,
entra al servicio en Render → pestaña **Environment** → copia el valor de `AGENTE_TOKEN`.
Ese mismo token va en la app Android.

**Límites del plan gratis de Render**:
- El servicio se duerme tras 15 min sin tráfico y tarda ~40s en despertar. Como los
  teléfonos hacen checkin cada 2 min, se mantiene despierto casi siempre.
- La base de datos gratuita caduca a los 30 días. Para un cliente de verdad, sube al
  plan de pago pequeño (~7 USD/mes) cuando empieces a cobrar.

## Desplegar en tu propio servidor

1. Copia el proyecto a tu servidor.
2. `cp backend/.env.example backend/.env` y edita:
   - `DJANGO_SECRET_KEY`: una cadena larga y aleatoria.
   - `AGENTE_TOKEN`: el token que usarán los teléfonos (cámbialo).
   - `ADMIN_USER` / `ADMIN_PASSWORD`: tu acceso al panel.
   - `DJANGO_ALLOWED_HOSTS`: el dominio del panel (ej.: `panel.tudominio.com`).
   - `CSRF_TRUSTED_ORIGINS`: `https://panel.tudominio.com`
3. `docker compose up --build -d`
4. El panel queda en el puerto 8000. Ponle un proxy con HTTPS delante (Caddy, Nginx, o el
   propio del hosting). El HTTPS es obligatorio porque la app envía el token.

El admin inicial se crea solo al arrancar, con las credenciales del `.env`.

## Flujo de uso

1. Entra al panel.
2. **Políticas → Crear**: define apps permitidas, kiosco y restricciones.
3. **Aplicaciones**: agrega los APKs que quieras poder instalar (URL pública con HTTPS).
4. Cuando un teléfono con Candado haga checkin, aparece en **Equipos**.
5. Abre un equipo: asígnale una política, instálale apps, bloquéalo o reinícialo.

## La app Android

La app (proyecto `candado-apk`) debe configurarse con:
- La **URL del panel** en el campo de sincronización: `https://tu-panel/`
- El **token** (`AGENTE_TOKEN`) — se añade en la ampliación de la app.

El endpoint que consume es `POST /api/checkin/` con cabecera `X-Token`.

## API para los teléfonos

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/checkin/` | Reporta estado; recibe política y comandos |
| POST | `/api/comando/{id}/resultado/` | Informa si un comando se completó |

Ambas requieren la cabecera `X-Token: <AGENTE_TOKEN>`.


## Aplicaciones (instalar apps en los equipos)

Los APK se alojan en una **URL pública con HTTPS** (tu Cloudflare Pages) y el panel
guarda las URLs. Los archivos no pasan por el servidor del panel (evita problemas de
memoria en hostings pequeños).

1. Sube el/los APK a tu Cloudflare Pages.
2. **Aplicaciones → Agregar**: nombre, paquete, URL del APK base, y si la app viene
   **dividida** de Google Play, las URLs de los splits (una por línea).
3. Entra a un equipo → **Instalar** → elige la app. Candado descarga los APK e instala,
   conservando la firma original (así siguen recibiendo actualizaciones).

**Extraer los APK de una app ya instalada** (para subirlos a Cloudflare):
```
adb shell pm path com.ejemplo.app      # lista los APK (base + splits)
adb pull /data/app/.../base.apk
adb pull /data/app/.../split_config.arm64_v8a.apk   # uno por cada split
```
