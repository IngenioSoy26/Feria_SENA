# GUÍA DE DESPLIEGUE EN PYTHONANYWHERE
## Sistema de Gestión - Feria de Proyectos Productivos SENA

> **Idioma:** Español  
> **Entorno:** PythonAnywhere (PaaS)  
> **Framework:** Django 4+  
> **Base de Datos destino:** PostgreSQL (recomendado) o MySQL  
> **Tiempo estimado:** 30 – 45 minutos

---

## PASO 1 – PRE-REQUISITOS ANTES DE EMPEZAR

Verifique que cuente con:

1. Cuenta activa en PythonAnywhere (gratuita o de pago).
2. Repositorio Git privado con el código del proyecto (`c:\Feria_2026`).
3. Archivo `requirements.txt` del proyecto.
4. Dominios o subdominio disponible si usa plan pago (opcional).
5. Nombres de variables de entorno listos para el `.env` de producción.

---

## PASO 2 – CREAR UN NUEVO WEB APP EN PYTHONANYWHERE

1. Inicie sesión en https://www.pythonanywhere.com.
2. Vaya al menú **Dashboard → Web**.
3. Pulse **Add a new web app**.
4. Seleccione: **Manual configuration** (configuración manual).
5. Seleccione la versión **Python 3.10** (coincidente con entorno local).
6. Finalice el asistente. No cierre la pestaña, volvemos aquí en el Paso 10.

---

## PASO 3 – CREAR ENTORNO VIRTUAL EN EL SERVIDOR

Desde la consola `Bash` de PythonAnywhere:

```bash
cd ~
mkvirtualenv --python=/usr/bin/python3.10 feria_sena_env
```

Verifique que el prompt empiece con `(feria_sena_env)`.

---

## PASO 4 – CLONAR EL REPOSITORIO O SUBIR EL CÓDIGO

### Opción A (recomendada) – Clonar desde Git:

```bash
cd ~
git clone https://USUARIO:TOKEN@github.com/TU_ORGANIZACION/Feria_2026.git Feria_2026
cd Feria_2026
git checkout main
```

### Opción B – Subir ZIP manual:

1. Menú **Files** → subir `Feria_2026.zip`.
2. En Bash:
   ```bash
   cd ~
   unzip Feria_2026.zip
   ```

---

## PASO 5 – INSTALAR DEPENDENCIAS EN ENTORNO VIRTUAL

```bash
workon feria_sena_env
cd ~/Feria_2026
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Validación rápida:**
```bash
python manage.py --version
```

---

## PASO 6 – CONFIGURAR ARCHIVO `.env` DE PRODUCCIÓN

```bash
cd ~/Feria_2026
cp .env.example .env
nano .env
```

Complete **al menos** estas variables (modifique los valores por los reales):

```dotenv
# --- Seguridad crítica ---
DJANGO_SECRET_KEY=CambiarESTEvalorPOR_UN_aleatorio_MUY_LARGO_2026_xyz
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=*.pythonanywhere.com,midominio.com

# --- Base de datos PostgreSQL (PAAS o MySQL según plan) ---
DB_ENGINE=django.db.backends.postgresql
DB_NAME=feria_sena_db
DB_USER=feria_sena_user
DB_PASSWORD=CAMBIAR_PASSWORD_SEGURO
DB_HOST=TU_HOST.postgres.pythonanywhere-services.com
DB_PORT=10001

# --- Miscelánea ---
DJANGO_TIME_ZONE=America/Bogota
DJANGO_LANGUAGE_CODE=es-CO
DJANGO_STATIC_URL=/static/
DJANGO_MEDIA_URL=/media/

# --- Admin (ocultar) ---
DJANGO_ADMIN_URL=panel-admin-secreto-2026/
```

Guarde con `Ctrl+O` → Enter → `Ctrl+X`.

---

## PASO 7 – CREAR / CONFIGURAR LA BASE DE DATOS

1. Vaya a **Dashboard → Databases** en PythonAnywhere.
2. Cree una base PostgreSQL (recomendado) o MySQL.
3. Anote credenciales y reemplace en el `.env` del Paso 6.
4. Regrese a la consola Bash y pruebe la conexión:

```bash
cd ~/Feria_2026
workon feria_sena_env
python manage.py check
```

Si retorna `System check identified no issues`, continue.

---

## PASO 8 – EJECUTAR MIGRACIONES DE BASE DE DATOS

```bash
cd ~/Feria_2026
workon feria_sena_env
python manage.py makemigrations
python manage.py migrate
```

**Importante:** Si usa MySQL + utf8, ejecute primero:
```bash
python -c "import django; django.setup(); from django.db import connection; print(connection.introspection.sequence_list())"
```

---

## PASO 9 – CARGAR DATOS MAESTROS Y DATOS DEMO (SEED)

Cree los roles de sistema y la data demo real:

```bash
python manage.py crear_roles_iniciales
python manage.py seed_demo
```

**Salida esperada del seed:**  
`✅ SEED DEMO COMPLETADO. Usuarios demo: admin_demo / registro_demo / ... | Password demo: DemoSena1234*`

**Produc:** recuerde cambiar contraseñas y usuarios demo antes del evento real.

---

## PASO 10 – CONFIGURAR EL WSGI FILE DE PYTHONANYWHERE

1. Abra **Dashboard → Web → WSGI configuration file** (ej: `/var/www/miusuario_pythonanywhere_com_wsgi.py`).
2. **Elimine todo el contenido por defecto** y pegue este bloque:

```python
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path("/home/miusuario/Feria_2026")
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE)

if BASE_DIR.as_posix() not in sys.path:
    sys.path.insert(0, BASE_DIR.as_posix())

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.production"

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

> ⚠ Cambie `miusuario` por su nombre de usuario real en PythonAnywhere.

---

## PASO 11 – VINCULAR ENTORNO VIRTUAL Y DIRECTORIO WORKING

1. **Dashboard → Web → Code**
   - **Source code:** `/home/miusuario/Feria_2026`
   - **Working directory:** `/home/miusuario/Feria_2026`
   - **Virtualenv path:** `/home/miusuario/.virtualenvs/feria_sena_env`

2. Guarde los cambios.

---

## PASO 12 – CONFIGURAR STATIC FILES (CSS / JS / PWA)

En **Dashboard → Web → Static files**, agregue 2 registros tal cual:

| URL                  | Directory                                           |
| -------------------- | --------------------------------------------------- |
| `/static/`           | `/home/miusuario/Feria_2026/static_collected`       |
| `/media/`            | `/home/miusuario/Feria_2026/media`                  |

> No olvide ejecutar collectstatic en el Paso 14.

---

## PASO 13 – AÑADIR WHITENOISE SI AÚN NO ESTÁ PRESENTE

WhiteNoise ya está configurado en `config/settings/base.py`. Si lo necesita, confirme:
```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    ...
]
```

---

## PASO 14 – EJECUTAR COLLECTSTATIC

```bash
cd ~/Feria_2026
workon feria_sena_env
python manage.py collectstatic --noinput
```

Debe ver: `XXX static files copied to '/home/miusuario/Feria_2026/static_collected'.`

---

## PASO 15 – CREAR SUPERUSUARIO PRODUCCIÓN

```bash
python manage.py createsuperuser
```

Sugerencia:
```
Username: superadmin_feria
Email: soporte@senaferia2026.edu.co
Password: (algo MUY seguro, no use DemoSena1234*)
```

---

## PASO 16 – FORZAR SSL / HTTPS (OBLIGATORIO PRODUCCIÓN)

Edite `config/settings/production.py` y agregue o confirme:

```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
```

En **Dashboard → Web → Security**, marque la opción **Force HTTPS** si su plan lo permite.

---

## PASO 17 – RECARGAR (RELOAD) LA APLICACIÓN Y PROBAR

1. Pulse el botón verde **Reload miusuario.pythonanywhere.com** en Dashboard → Web.
2. Abra en navegador privado:
   - `https://miusuario.pythonanywhere.com/accounts/login/`
3. Inicie sesión con `admin_demo / DemoSena1234*` (si mantuvo el seed).
4. Pruebe:
   - ✅ Panel Dashboard
   - ✅ Registro → crear una institución nueva
   - ✅ Operador Refrigerios → entregue 1 refrigerio
   - ✅ Operador Certificados → entregue 1 certificado
   - ✅ 403 al intentar cruzar roles (ver tests/test_rbac_403.py)
   - ✅ PWA → instalar desde menú Chrome «Instalar App»

---

## PASO 18 – MANTENIMIENTO POST-DESPLIEGUE (CHECKLIST SEMANAL)

1. **Backup de la BD:**  
   `pg_dump feria_sena_db > backup-feria-$(date +%F).sql` (Postgres).
2. **Logs:** Revise **Dashboard → Web → Log files** por errores 500.
3. **Logs auditoría:** Revise `apps/auditoria/` por acciones sospechosas.
4. **Renovar SSL:** Renove antes del vencimiento.
5. **Actualizar paquetes:**  
   ```bash
   workon feria_sena_env
   cd ~/Feria_2026
   pip list --outdated
   pip install -U paquete_seguro
   ```
6. **Usuarios demo:** Antes del evento real **eliminar o cambiar password** a:
   ```bash
   python manage.py changepassword admin_demo
   python manage.py changepassword registro_demo
   ...
   ```
7. **Staticfiles nuevos:** Siempre re-ejecute `collectstatic` tras cambios de CSS/JS.
8. **Reload:** Después de **cualquier** cambio en código → pulse **Reload** del Web App.

---

## ANEXO: COMANDOS RÁPIDOS (CHEATSHEET)

```bash
# Entrar al entorno
workon feria_sena_env
cd ~/Feria_2026

# Después de git pull
git pull origin main
python manage.py migrate
python manage.py collectstatic --noinput
# ... pulsar Reload en Web App

# Ejecutar tests
python manage.py test tests -v 2

# Ejecutar seed (cuidado en prod)
python manage.py seed_demo
```

---

Fin del documento – Fecha guía: Octubre 2026 – Proyecto SENA Feria La Guajira.
