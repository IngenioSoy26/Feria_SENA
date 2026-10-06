import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-sena-feria-2026-cambiar-en-produccion'
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'csp',
    'apps.core',
    'apps.usuarios',
    'apps.eventos',
    'apps.instituciones',
    'apps.programas',
    'apps.personas',
    'apps.proyectos',
    'apps.instructores',
    'apps.invitados',
    'apps.escarapelas',
    'apps.asistencia',
    'apps.refrigerios',
    'apps.certificados',
    'apps.dashboard',
    'apps.reportes',
    'apps.auditoria',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config.middleware.AuditoriaMiddleware',
    'config.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'config.context_processors.evento_activo',
                'config.context_processors.menu_dinamico_por_rol',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

LANGUAGE_CODE = os.environ.get('DJANGO_LANGUAGE_CODE', 'es-CO')
TIME_ZONE = os.environ.get('DJANGO_TIME_ZONE', 'America/Bogota')
USE_I18N = True
USE_TZ = True

STATIC_URL = os.environ.get('DJANGO_STATIC_URL', '/static/')
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'static_collected'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = os.environ.get('DJANGO_MEDIA_URL', '/media/')

TOKEN_REGISTRO_PUBLICO = (os.environ.get('TOKEN_REGISTRO', '') or '').strip()
TOKEN_OPERADORES_PUBLICO = (os.environ.get('TOKEN_OPERADORES', '') or '').strip()
MEDIA_ROOT = BASE_DIR / 'media'

try:
    MAX_APRENDICES_POR_PROYECTO = max(1, min(99, int(os.environ.get('MAX_APRENDICES_POR_PROYECTO', '3'))))
except (ValueError, TypeError):
    MAX_APRENDICES_POR_PROYECTO = 3

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'usuarios.Usuario'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = 'simple:home'
LOGOUT_REDIRECT_URL = '/accounts/login/'

CSP_DEFAULT_SRC = ("'self'", "*")
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://fonts.googleapis.com", "https://cdn.jsdelivr.net", "*")
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net", "https://unpkg.com", "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/", "https://cdn.jsdelivr.net/npm/html5-qrcode@2.3.8/", "*")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com", "https://fonts.googleapis.com", "data:", "*")
CSP_IMG_SRC = ("'self'", "data:", "https://cdn.jsdelivr.net", "*")
CSP_CONNECT_SRC = ("'self'", "*")
CSP_FRAME_ANCESTORS = ("'self'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
CSP_INCLUDE_NONCE_IN = []

SESSION_COOKIE_AGE = 86400
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
