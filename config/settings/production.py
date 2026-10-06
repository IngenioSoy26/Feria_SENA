import os
from pathlib import Path

from .base import *

# ============================================================
# SENA FERIA 2026 - CONFIGURACIÓN PRODUCCIÓN (Railway)
# Última revisión: 2026-10-06
# ============================================================

DEBUG = False

# ------------------------------------------------------------
# HOSTS PERMITIDOS (separados por coma sin espacios)
# Railway inyecta RAILWAY_PUBLIC_DOMAIN automáticamente; lo añadimos
# para no forzar al usuario editar esta variable en cada deploy.
# ------------------------------------------------------------
_allowed_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]
_railway_domain = os.environ.get('RAILWAY_PUBLIC_DOMAIN', '').strip()
if _railway_domain and _railway_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_domain)
# Fallback seguro para entorno Railway sin dominio configurado:
if not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [
        '*.railway.app',
        '*.up.railway.app',
    ]

# ------------------------------------------------------------
# CSRF (orígenes de los formularios)
# ------------------------------------------------------------
_csrf_raw = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [h.strip() for h in _csrf_raw.split(',') if h.strip()]
if _railway_domain:
    for proto in ('https://', 'http://'):
        u = proto + _railway_domain
        if u not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(u)
if not CSRF_TRUSTED_ORIGINS and _railway_domain:
    CSRF_TRUSTED_ORIGINS = [
        f'https://{_railway_domain}',
        f'https://*.railway.app',
    ]
# Use X-Forwarded-Host de Railway proxy cuando haga falta:
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ------------------------------------------------------------
# ARCHIVOS ESTÁTICOS (WhiteNoise comprimidos + cache manifest)
# ------------------------------------------------------------
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# Directorios extra (settings/base ya trae static/, pero aseguramos):
if not STATICFILES_DIRS:
    STATICFILES_DIRS = [BASE_DIR / 'static']

# ------------------------------------------------------------
# BASE DE DATOS
# Orden de precedencia:
#   1. DATABASE_URL (variable estándar Railway / Render / Heroku, inyectada al
#      activar el Add-on Postgres de Railway; prefijo postgres:// → parse ok)
#   2. DJANGO_DB_ENGINE + 5 variables individuales (legacy PythonAnywhere)
#   3. SQLite db.sqlite3 local (fallback absoluto que NUNCA debe usarse en
#      producción concurrente pero evita 500 si se olvida configurar vars).
# Nota: `base.py` NO define DATABASES por defecto; cada entorno define la suya.
# ------------------------------------------------------------
import dj_database_url

DATABASES = {}
_db_url = os.environ.get('DATABASE_URL', '').strip()
_db_engine_explicit = os.environ.get('DJANGO_DB_ENGINE', '').strip()

if _db_url:
    # Railway inyecta postgres:// que dj_database_url soporta;
    # además activamos sslmode prefer para Postgres cloud.
    _opts = {}
    if _db_url.startswith('postgres'):
        _opts['sslmode'] = os.environ.get('PGSSLMODE', 'require')
    DATABASES['default'] = dj_database_url.config(
        default=_db_url,
        conn_max_age=600,
        conn_health_checks=True,
    )
    if _opts:
        DATABASES['default'].setdefault('OPTIONS', {}).update(_opts)
elif _db_engine_explicit:
    DATABASES['default'] = {
        'ENGINE': _db_engine_explicit,
        'NAME': os.environ.get('DJANGO_DB_NAME', ''),
        'USER': os.environ.get('DJANGO_DB_USER', ''),
        'PASSWORD': os.environ.get('DJANGO_DB_PASSWORD', ''),
        'HOST': os.environ.get('DJANGO_DB_HOST', 'localhost'),
        'PORT': os.environ.get('DJANGO_DB_PORT', ''),
        'ATOMIC_REQUESTS': True,
    }
else:
    # Fallback de seguridad: SQLite (NO recomendado para más de 2 celulares
    # simultáneos en escritura). Se usa solo en entornos de prueba sin vars.
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {'timeout': 30},
        'ATOMIC_REQUESTS': True,
    }
# Siempre activar atomic requests en producción para evitar transacciones
# a medio hacer en 500s parciales:
if not DATABASES['default'].get('ATOMIC_REQUESTS'):
    DATABASES['default']['ATOMIC_REQUESTS'] = True

# ------------------------------------------------------------
# EMAIL (opcional — por defecto consola para no fallar sin SMTP)
# ------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', '')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.environ.get('DJANGO_EMAIL_USE_TLS', 'True') == 'True'
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'no-responder@senaferia.edu.co')

# ------------------------------------------------------------
# SEGURIDAD HTTPS / COOKIES / CABECERAS
# ------------------------------------------------------------
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True') == 'True'
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_AGE = 4 * 60 * 60  # 4 horas de sesión activa (evento feria)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ------------------------------------------------------------
# LOGGING PRODUCCIÓN (Railway captura stdout en Metrics → Logs)
# ------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.environ.get('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}
