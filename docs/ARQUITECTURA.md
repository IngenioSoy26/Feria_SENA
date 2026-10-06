# SISTEMA DE GESTIÓN FERIA PROYECTOS PRODUCTIVOS SENA

## Identidad Visual

| Elemento | Valor |
|---|---|
| Color Institucional SENA | `#39A900` (Verde SENA) |
| Tipografía Principal | **Work Sans** (Google Fonts) |
| Paleta Complementaria | `#FFFFFF` (Blanco), `#212529` (Negro Bootstrap), `#6C757D` (Gris) |
| Acento Secundario | `#FFC107` (Warning Bootstrap), `#DC3545` (Danger Bootstrap) |

---

## 1. RESUMEN FUNCIONAL

El **Sistema de Gestión Feria Proyectos Productivos SENA** es una plataforma web monolítica desarrollada en Django 5, diseñada para administrar el ciclo completo de una feria de proyectos del Servicio Nacional de Aprendizaje (SENA). El sistema integra la gestión de participantes, instituciones, programas de formación, proyectos, eventos, asistencia, refrigerios, escarapelas, certificados, auditoría y generación de reportes estadísticos.

### Módulos Funcionales Clave:

1. **Usuarios y Autenticación** — Gestión de cuentas, roles (Administrador, Coordinador, Instructor, Aprendiz, Invitado), restablecimiento de contraseñas y login.
2. **Instituciones y Programas** — CRUD de centros de formación, regionales y programas de formación (Técnico, Tecnólogo, Especialización).
3. **Personas** — Registro y administración de aprendices, instructores, jurados, visitantes y coordinadores con datos biográficos completos.
4. **Proyectos** — Registro, categorización, asignación de responsables, jurados y estado del proyecto (inscrito, aprobado, en evaluación, premiado).
5. **Eventos** — Programación de ferias, agenda, sedes, salones y horarios por día.
6. **Escarapelas** — Generación dinámica de escarapelas personalizadas con código QR, nombre, rol, programa y código de barras.
7. **Asistencia** — Registro de entrada/salida mediante escaneo de QR (cámara web o móvil), validación en tiempo real y lista de asistencia.
8. **Refrigerios** — Control de entrega de refrigerios por evento, conteo de raciones distribuidas y reportes de consumo.
9. **Certificados** — Generación automatizada de certificados de asistencia y participación con validación por código único.
10. **Dashboard** — Panel estadístico en tiempo real con gráficos interactivos (asistencia, proyectos por categoría, participación por regional).
11. **Reportes** — Generación de reportes PDF y Excel personalizables por módulo.
12. **Auditoría** — Registro cronológico de todas las acciones del sistema (quién hizo qué, cuándo y desde qué IP).

---

## 2. STACK TECNOLÓGICO

### Backend

| Tecnología | Versión | Propósito |
|---|---|---|
| **Django** | 5.1 LTS | Framework web principal: ORM, MVT, Auth, Admin, Signals, Middleware, Forms |
| **Python** | 3.12+ | Lenguaje de ejecución del backend |
| **SQLite** | 3.45+ | Motor de base de datos (desarrollo / producción pequeña escala) |
| **ReportLab** | 4.2+ | Generación de documentos PDF (certificados, reportes, escarapelas) |
| **openpyxl** | 3.1+ | Lectura y escritura de archivos Excel (reportes, importación masiva) |
| **qrcode** | 7.4+ | Generación de códigos QR para escarapelas y certificados |
| **Pillow** | 10.4+ | Procesamiento de imágenes (logos, firmas, fotografías, composición de escarapelas) |
| **whitenoise** | 6.7+ | Servicio de archivos estáticos sin necesidad de servidor web adicional |
| **python-dotenv** | 1.0+ | Gestión de variables de entorno segregadas por ambiente |

### Frontend (Integrado en Templates Django)

| Tecnología | Versión | Propósito |
|---|---|---|
| **Bootstrap 5** | 5.3.3 | Framework CSS responsivo: grid, componentes, utilidades |
| **Chart.js** | 4.4.3 | Librería de gráficos interactivos (barras, líneas, doughnut, radar) |
| **html5-qrcode** | 2.3.8 | Escaneo de códigos QR desde cámara web en navegador |
| **HTML5** | — | Marcado semántico, accesibilidad ARIA |
| **CSS3** | — | Estilos personalizados sobre identidad visual SENA |
| **JavaScript (Vanilla)** | ES6+ | Interactividad cliente-side sin frameworks pesados |

### Infraestructura

| Componente | Proveedor / Tipo |
|---|---|
| Servidor de Aplicaciones | **PythonAnywhere** (Plataforma como Servicio - PaaS) |
| Servidor WSGI | Gunicorn / uWSGI (gestionado por PythonAnywhere) |
| Dominio / HTTPS | Let's Encrypt (gestionado por PythonAnywhere) |
| Almacenamiento | Disco local PythonAnywhere + Media files |
| Backup | PythonAnywhere Daily Snapshot + Export SQLite |

---

## 3. ARQUITECTURA DE SETTINGS (MULTI-AMBIENTE)

Se adopta la estrategia **base/development/production** para separar configuraciones por ambiente, evitando duplicación y minimizando errores de despliegue.

```
Feria_2026/
├── config/                          # App de configuración global
│   ├── settings/                    # PAQUETE settings (no archivo único)
│   │   ├── __init__.py
│   │   ├── base.py                  # Configuración común (TODOS los ambientes)
│   │   ├── development.py           # Configuración local de desarrollo
│   │   └── production.py            # Configuración para PythonAnywhere
│   ├── urls.py                      # Enrutador global
│   ├── wsgi.py                      # Entrypoint WSGI
│   └── asgi.py                      # Entrypoint ASGI (para futuro)
```

### Regla de Activación:

`manage.py` y `wsgi.py` apuntan a `DJANGO_SETTINGS_MODULE=config.settings.development` por defecto. En producción, PythonAnywhere configura la variable de entorno `DJANGO_SETTINGS_MODULE=config.settings.production`.

### Variables de Entorno (.env) — Gestionadas con python-dotenv:

```dotenv
# .env (NO versionar en Git - AGREGAR al .gitignore)
SECRET_KEY='tu-clave-secreta-aqui-50+caracteres'
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,.pythonanywhere.com
DATABASE_NAME=db.sqlite3
DB_BACKUP_DIR=backups/
ADMIN_URL=sistema-admin-secreto/
SESSION_COOKIE_AGE=3600
```

### base.py (Ajustes Comunes):

- `INSTALLED_APPS` declarados aquí, incluyendo todas las 13 apps funcionales.
- `MIDDLEWARE` con `SecurityMiddleware`, `SessionMiddleware`, `CsrfViewMiddleware`, `AuthMiddleware`, `WhiteNoiseMiddleware`.
- `AUTH_USER_MODEL = 'usuarios.Usuario'` (modelo personalizado).
- `TIME_ZONE = 'America/Bogota'`, `USE_I18N = True`, `LANGUAGE_CODE = 'es-co'`.
- `STATIC_URL`, `MEDIA_URL`, `STATICFILES_DIRS`, `STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'`.

### development.py:

- `DEBUG = True`, `ALLOWED_HOSTS = ['localhost', '127.0.0.1']`
- `DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}`
- `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` (pruebas locales)
- `INSTALLED_APPS += ['django_extensions']` (herramientas de desarrollo opcional)

### production.py:

- `DEBUG = False`, `ALLOWED_HOSTS` leído desde `.env`
- `SECURE_SSL_REDIRECT = True`, `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
- `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`
- `SECURE_BROWSER_XSS_FILTER = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `X_FRAME_OPTIONS = 'DENY'`
- `EMAIL_BACKEND` configurado con SMTP real (configurable)
- Conexión a base de datos SQLite optimizada con `timeout` y `journal_mode=WAL`

---

## 4. ESTRUCTURA DE APLICACIONES (13 MÓDULOS)

```
Feria_2026/                         # Raíz del proyecto Django
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
├── static/                         # Archivos estáticos GLOBALES
│   ├── css/
│   │   └── sena.css                # Identidad visual SENA (#39A900 + Work Sans)
│   ├── js/
│   │   ├── qr-scanner.js
│   │   └── dashboard-charts.js
│   └── img/
│       ├── logo-sena.svg
│       └── logo-ministerio.svg
├── media/                          # Uploads de usuarios (fotos, firmas, evidencias)
├── templates/                      # Plantillas GLOBALES (base.html, 403.html, etc.)
│   ├── base.html                   # Plantilla maestra (Navbar + Footer + Assets)
│   ├── 403.html
│   ├── 404.html
│   ├── 500.html
│   ├── registration/
│   │   └── login.html
│   └── partials/
│       ├── navbar.html
│       ├── sidebar.html
│       └── messages.html
├── config/                         # App CORE de configuración (settings + URLs)
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── core/                           # Mixins, decorators, utilidades TRANSVERSALES
│   ├── models.py                   # TimeStampedModel, SoftDeleteModel (base)
│   ├── mixins.py                   # LoginRequiredMixin, GroupRequiredMixin (RBAC)
│   ├── decorators.py               # @require_group, @audit_action
│   ├── utils.py                    # qr_generator, pdf_utils, excel_exporter
│   ├── templatetags/
│   │   └── sena_filters.py         # Filtros Jinja2 personalizados
│   └── constants.py                # ROLES_SENA, ESTADOS_PROYECTO, etc.
├── usuarios/                       # Gestión de Usuarios y Roles (RBAC)
│   ├── models.py                   # Usuario(AbstractUser), Perfil, Rol
│   ├── forms.py
│   ├── views.py
│   ├── admin.py
│   ├── urls.py
│   └── templates/usuarios/
├── instituciones/                  # Regionales, Centros de Formación, Sedes
│   ├── models.py                   # Regional, Centro, Sede, Ambiente
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/instituciones/
├── programas/                      # Programas de Formación SENA
│   ├── models.py                   # NivelFormacion, ProgramaFicha, Ficha
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/programas/
├── personas/                       # Aprendices, Instructores, Jurados, Visitantes
│   ├── models.py                   # Persona, Aprendiz, Instructor, Jurado, Visitante
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/personas/
├── proyectos/                      # Proyectos Productivos
│   ├── models.py                   # CategoriaProyecto, Proyecto, Integrante, Evaluacion, Premio
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/proyectos/
├── eventos/                        # Feria, agenda, actividades, horarios
│   ├── models.py                   # Feria, DiaEvento, Actividad, Ponente, Lugar
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/eventos/
├── escarapelas/                    # Generación y descarga de escarapelas con QR
│   ├── models.py                   # PlantillaEscarapela, EscarapelaGenerada
│   ├── generators.py               # Lógica de composición PDF/PNG con Pillow + QR
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/escarapelas/
├── asistencia/                     # Registro de entrada/salida por QR
│   ├── models.py                   # RegistroAsistencia, PuntoControl
│   ├── scanner.py                  # Lógica de validación QR
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/asistencia/
│       └── scanner.html            # Integración html5-qrcode
├── refrigerios/                    # Control de refrigerios entregados
│   ├── models.py                   # TipoRefrigerio, LoteRefrigerio, EntregaRefrigerio
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/refrigerios/
├── certificados/                   # Certificados PDF con validación única
│   ├── models.py                   # PlantillaCertificado, Certificado, CodigoValidacion
│   ├── generators.py               # ReportLab + QR código validación
│   ├── forms.py, views.py, urls.py, admin.py
│   └── templates/certificados/
├── dashboard/                      # Dashboard estadístico con Chart.js
│   ├── views.py                    # Consultas agregadas ORM
│   ├── urls.py
│   ├── serializers.py              # Datos JSON para Chart.js
│   └── templates/dashboard/
│       └── home.html
├── reportes/                       # Generación de reportes PDF/Excel
│   ├── views.py
│   ├── urls.py
│   ├── reports_pdf.py              # ReportLab builders
│   ├── reports_xlsx.py             # openpyxl builders
│   └── templates/reportes/
└── auditoria/                      # Registro de auditoría completo
    ├── models.py                   # RegistroAuditoria (actor, acción, modelo, IP, fecha)
    ├── middleware.py               # Intercepta requests y loguea acciones
    ├── signals.py                  # Signals pre_save/post_delete para modelos clave
    ├── admin.py, urls.py, views.py
    └── templates/auditoria/
```

### Responsabilidades por App:

| App | Propósito Transversal | Dependencias Principales |
|---|---|---|
| **config** | Enrutamiento global, settings multi-ambiente, WSGI | Ninguna |
| **core** | Clases base (modelos abstractos), mixins RBAC, utilidades PDF/QR/Excel | Ninguna (base de todo) |
| **usuarios** | `AUTH_USER_MODEL` personalizado, grupos Django (Admin, Coordinador, Instructor, Aprendiz, Jurado, Visitante) | core |
| **instituciones** | Árbol organizacional SENA: Regional → Centro → Sede → Ambiente | core, usuarios |
| **programas** | Niveles de formación + Programas + Fichas grupales | core, instituciones |
| **personas** | Herencia: Persona abstracta → Aprendiz / Instructor / Jurado / Visitante | core, instituciones, programas, usuarios |
| **proyectos** | Proyectos productivos con integrantes, evaluaciones, premios, categorías | core, personas, programas, instituciones |
| **eventos** | Feria como unidad de edición, agenda por día, lugares | core, instituciones |
| **escarapelas** | Composición PDF: logo SENA + foto + datos + QR único | core, personas, eventos (Pillow + qrcode + ReportLab) |
| **asistencia** | Puntos de control, scanner QR, timestamp entrada/salida | core, personas, eventos (html5-qrcode en template) |
| **refrigerios** | Inventario mínimo y registro de entrega por asistente validado | core, asistencia, eventos |
| **certificados** | Plantillas, generación PDF, código de validación públicamente verificable | core, personas, proyectos, eventos |
| **dashboard** | KPIs y gráficos de: asistencia, proyectos, participantes, refrigerios | TODAS (consultas de solo lectura) |
| **reportes** | Exportadores modulares PDF/Excel por dominio | TODAS + ReportLab + openpyxl |
| **auditoria** | Log íntegro de cambios por usuario, IP y timestamp | TODAS (middleware + signals) |

---

## 5. DIAGRAMA DE ARQUITECTURA (TEXTO ASCII)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          CLIENTE (NAVEGADOR WEB)                             │
│  Chrome / Edge / Firefox / Safari  ·  Desktop · Tablet · Móvil               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │  FRONTEND (Django Templates)                                        │    │
│  │  ┌───────────┐ ┌───────────┐ ┌────────────┐ ┌────────────────────┐  │    │
│  │  │ Bootstrap │ │ Chart.js  │ │html5-qrcode│ │  CSS SENA #39A900  │  │    │
│  │  │   5.3     │ │   4.4     │ │   2.3      │ │  Work Sans (Font)  │  │    │
│  │  └─────┬─────┘ └─────┬─────┘ └─────┬──────┘ └────────┬───────────┘  │    │
│  │        └─────────────┴─────────────┴─────────────────┘              │    │
│  └───────────────────────────────────┬──────────────────────────────────┘    │
│                                      │ HTTPS / TLS 1.3                        │
└──────────────────────────────────────┼───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                      PYTHONANYWHERE (PAAS - PRODUCCIÓN)                      │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  WSGI SERVER (Gunicorn gestionado)                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  DJANGO 5.1 LTS  ·  Python 3.12                                  │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  MIDDLEWARE STACK (orden estricto)                        │  │  │  │
│  │  │  │  1. SecurityMiddleware   (HTTPS/HSTS/XSS/CSRF)            │  │  │  │
│  │  │  │  2. WhiteNoiseMiddleware  (Static files comprimidos)      │  │  │  │
│  │  │  │  3. SessionMiddleware     (Sesiones seguras)              │  │  │  │
│  │  │  │  4. CsrfViewMiddleware    (Tokens CSRF en formularios)    │  │  │  │
│  │  │  │  5. AuthMiddleware        (Usuario autenticado en request)│  │  │  │
│  │  │  │  6. MessageMiddleware     (Mensajes flash)                │  │  │  │
│  │  │  │  7. AuditoriaMiddleware   (Logging de acciones)           │  │  │  │
│  │  │  │  8. XFrameOptionsMiddleware (Clickjacking)                │  │  │  │
│  │  │  └───────────────────────────┬────────────────────────────────┘  │  │  │
│  │  │                              ▼                                    │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  URL ROUTER (config/urls.py)                               │  │  │  │
│  │  │  │  ├── /admin-secreto/     › Django Admin (usuarios staff)   │  │  │  │
│  │  │  │  ├── /usuarios/          › App usuarios                   │  │  │  │
│  │  │  │  ├── /instituciones/     › App instituciones              │  │  │  │
│  │  │  │  ├── /programas/         › App programas                  │  │  │  │
│  │  │  │  ├── /personas/          › App personas                   │  │  │  │
│  │  │  │  ├── /proyectos/         › App proyectos                  │  │  │  │
│  │  │  │  ├── /eventos/           › App eventos                    │  │  │  │
│  │  │  │  ├── /escarapelas/       › App escarapelas                │  │  │  │
│  │  │  │  ├── /asistencia/        › App asistencia + QR scanner    │  │  │  │
│  │  │  │  ├── /refrigerios/       › App refrigerios                │  │  │  │
│  │  │  │  ├── /certificados/      › App certificados               │  │  │  │
│  │  │  │  ├── /dashboard/         › App dashboard (Chart.js JSON)  │  │  │  │
│  │  │  │  ├── /reportes/          › App reportes (PDF/XLSX)        │  │  │  │
│  │  │  │  ├── /auditoria/         › App auditoría                  │  │  │  │
│  │  │  │  └── /                   › Dashboard home (login)         │  │  │  │
│  │  │  └───────────────────────────┬────────────────────────────────┘  │  │  │
│  │  │                              ▼                                    │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  VIEWS → FORMS → ORM → MODELS (13 Apps)                    │  │  │  │
│  │  │  │  RBAC via decorators/group_required_mixin                  │  │  │  │
│  │  │  │  Signals: auditoría, actualización de contadores          │  │  │  │
│  │  │  └───────────────────────────┬────────────────────────────────┘  │  │  │
│  │  └───────────────────────────────┼──────────────────────────────────┘  │  │
│  └──────────────────────────────────┼─────────────────────────────────────┘  │
│                                     ▼                                        │
│  ┌───────────────────────┐  ┌───────────────┐  ┌────────────────────────┐  │
│  │  BASE DE DATOS SQLite │  │  MEDIA FILES  │  │  STATIC FILES          │  │
│  │  · db.sqlite3         │  │  · fotos/     │  │  (servidos por         │  │
│  │  · WAL journal_mode   │  │  · firmas/    │  │   WhiteNoise comprim) │  │
│  │  · FK constraints ON  │  │  · evidencias/│  │  · sena.css            │  │
│  │  · foreign_key_checks │  │  · uploads/   │  │  · Chart.js/Bootstrap  │  │
│  └───────────┬───────────┘  └───────┬───────┘  └───────────┬────────────┘  │
└──────────────┼──────────────────────┼──────────────────────┼────────────────┘
               │                      │                      │
               ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  CAPA DE UTILIDADES / LIBRERÍAS ESPECIALIZADAS                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ ReportLab│ │ openpyxl │ │ qrcode   │ │ Pillow   │ │ python-dotenv     │  │
│  │  PDF     │ │  XLSX    │ │  QR      │ │  Img     │ │  ENV config      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. ARQUITECTURA DE DATOS (ESQUEMA RELACIONAL — RESUMEN)

```
Usuario (usuarios) 1─────1 Perfil (usuarios)
       │
       │ Auth: groups (Django Groups) = [Admin, Coordinador, Instructor,
       │                                  Aprendiz, Jurado, Visitante]
       ▼
Regional (instituciones) 1─────n Centro 1─────n Sede 1─────n Ambiente
       ▲                                                    ▲
       │                                                    │
       └────────────────────────────────────────── ProgramaFicha (programas)
                                                          │
                                                          └──── n Ficha (grupo)
                                                                   │
Persona (abstracta core)                                           ▼
 ├── Aprendiz (personas) n──────1 Ficha
 ├── Instructor (personas) n──────1 Centro
 ├── Jurado (personas)     n──────m Proyecto
 └── Visitante (personas)

CategoriaProyecto (proyectos) 1─────n Proyecto 1─────n Integrante (Aprendiz/Instructor)
                                           │
                                           └─────n Evaluacion (Jurado + puntaje)
                                           └─────1 Premio (opcional)

Feria (eventos) 1─────n DiaEvento 1─────n Actividad (lugar + horario)
    │
    ├─ n PuntoControl (asistencia) ── n RegistroAsistencia (Persona + timestamp)
    │                                                     │
    │                                                     └─ 0..1 EntregaRefrigerio
    ├─ n PlantillaEscarapela ── EscarapelaGenerada (PDF/PNG + QR)
    └─ n PlantillaCertificado ── Certificado (Persona + codigo_validacion unico)
```

---

## 7. PWA (PROGRESSIVE WEB APP)

El sistema se integra como **PWA de lectura básica** sin frameworks adicionales, usando solo Django Templates + Service Worker registrado en JavaScript. Esto permite instalación en móviles/escritorio y funcionamiento offline de la pantalla inicial de escaneo QR.

### Archivos PWA:

```
static/
├── js/
│   └── pwa-sw.js              # Service Worker (caching estratégico)
├── manifest.json              # Manifesto PWA (nombre, colores, íconos)
└── icons/
    ├── icon-192.png           # Ícono SENA 192x192
    ├── icon-512.png           # Ícono SENA 512x512
    └── icon-maskable.png      # Icono máscara adaptativa Android/iOS
```

### manifest.json:

```json
{
  "name": "Feria Proyectos Productivos SENA",
  "short_name": "Feria SENA",
  "description": "Sistema de Gestión de Feria de Proyectos del SENA",
  "start_url": "/dashboard/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#FFFFFF",
  "theme_color": "#39A900",
  "lang": "es-CO",
  "dir": "ltr",
  "icons": [
    {"src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "/static/icons/icon-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
```

### Estrategia de Caching (Service Worker):

- **Cache First**: `static/` CSS, JS, fuentes, imágenes del tema (Work Sans, logo SENA).
- **Network First**: HTML dinámico, peticiones POST (asistencia, login), API dashboard JSON.
- **Offline Fallback**: Pantalla informativa cuando no hay conexión, mostrando último dashboard cacheado + aviso de modo lectivo.

### Registro en base.html:

```html
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#39A900">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
<script>
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/static/js/pwa-sw.js');
    });
  }
</script>
```

---

## 8. DESPLIEGUE EN PYTHONANYWHERE

### 8.1 Pre-requisitos antes del despliegue:

1. Ejecutar localmente: `python manage.py check --deploy` (todas las validaciones de seguridad deben pasar en verde).
2. `python manage.py collectstatic --noinput` (genera `staticfiles/` comprimidos por WhiteNoise).
3. Ejecutar migraciones: `python manage.py migrate --plan` (validar plan).
4. Crear súper usuario: `python manage.py createsuperuser` (guardar credenciales en gestor de contraseñas, NO en texto plano).

### 8.2 Estructura en PythonAnywhere:

```
/home/tu-usuario-pythonanywhere/
├── Feria_2026/                    # Repositorio clonado desde Git
│   ├── manage.py
│   ├── config/
│   ├── apps...
│   ├── staticfiles/               # Resultado de collectstatic
│   ├── media/
│   ├── db.sqlite3                 # Producción
│   └── .env                       # Configurado a mano (sin versionar)
├── backups/                       # Fuera del proyecto (exportaciones diarias)
└── logs/
    ├── feria-sena-error.log
    └── feria-sena-access.log
```

### 8.3 Configuración WSGI PythonAnywhere (`/var/www/tu-usuario_pythonanywhere_com_wsgi.py`):

```python
import os
import sys

path = '/home/tu-usuario/Feria_2026'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.production'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 8.4 Web Tab PythonAnywhere:

| Campo | Valor |
|---|---|
| **Source Code** | `/home/tu-usuario/Feria_2026` |
| **Working Directory** | `/home/tu-usuario/Feria_2026` |
| **Virtualenv** | `/home/tu-usuario/.virtualenvs/feria-sena` (Python 3.12) |
| **WSGI Config File** | Path por defecto (editado según 8.3) |
| **Static Files → URL** | `/static/` |
| **Static Files → Directory** | `/home/tu-usuario/Feria_2026/staticfiles/` |
| **Static Files → URL** | `/media/` |
| **Static Files → Directory** | `/home/tu-usuario/Feria_2026/media/` |
| **Force HTTPS** | ✅ Activado (SecurityMiddleware refuerzo adicional) |

### 8.5 Script de Actualización (deploy.sh):

```bash
#!/bin/bash
cd /home/tu-usuario/Feria_2026
source /home/tu-usuario/.virtualenvs/feria-sena/bin/activate
git pull origin main
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput --clear
python manage.py check --deploy
```

### 8.6 Backup Automatizado (cron diario PythonAnywhere Scheduled Tasks):

```bash
#!/bin/bash
# backup_diario.sh - ejecutar a las 2:00 AM hora Colombia
DATE=$(date +%Y%m%d_%H%M)
BACKUP_DIR="/home/tu-usuario/backups"
PROJECT_DIR="/home/tu-usuario/Feria_2026"

mkdir -p "$BACKUP_DIR"
cp "$PROJECT_DIR/db.sqlite3" "$BACKUP_DIR/db_$DATE.sqlite3"
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" -C "$PROJECT_DIR" media
gzip -c "$PROJECT_DIR/db.sqlite3" > "$BACKUP_DIR/db_$DATE.sqlite3.gz"

# Retener solo los últimos 14 días
find "$BACKUP_DIR" -name "*.sqlite3" -mtime +14 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +14 -delete
find "$BACKUP_DIR" -name "*.gz" -mtime +14 -delete
```

---

## 9. SEGURIDAD

### 9.1 CSRF (Cross-Site Request Forgery) — Protección Total

- **Middleware**: `CsrfViewMiddleware` activado GLOBALMENTE en `base.py` (nunca desactivar).
- **Templates**: Todo `<form>` renderizado incluye `{% csrf_token %}` obligatorio.
- **AJAX**: Fetch/axios envía encabezado `X-CSRFToken` desde cookie `csrftoken`.
- **Cookies**: En producción `CSRF_COOKIE_SECURE = True`, `CSRF_COOKIE_HTTPONLY = False` (requerido por JS fetch), `CSRF_COOKIE_SAMESITE = 'Lax'`, `CSRF_TRUSTED_ORIGINS` configurado.
- **Excepciones**: NINGUNA. Si una vista necesita excepción, debe justificarse y usar `@csrf_exempt` únicamente sobre webhooks validados por firma (sin endpoints de usuario).

### 9.2 XSS (Cross-Site Scripting) — Tres Capas

1. **Autoescape Jinja2/Django Templates**: Activado por defecto. Solo usar `|safe` con contenido 100% controlado y sanitizado (no input de usuario).
2. **Middleware**: `SECURE_BROWSER_XSS_FILTER = True` (cabecera X-XSS-Protection: 1; mode=block).
3. **Sanitización en Forms/Vistas**: `django.utils.html.escape()` sobre cualquier texto renderizado sin plantilla.
4. **CSP (Content Security Policy)**: Implementado vía middleware con cabeceras estrictas:
   - `default-src 'self'`
   - `script-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'` (Chart.js, Bootstrap CDN)
   - `style-src 'self' https://cdn.jsdelivr.net https://fonts.googleapis.com 'unsafe-inline'`
   - `font-src 'self' https://fonts.gstatic.com`
   - `img-src 'self' data:` (QR codes generados como data URI)
   - `connect-src 'self'`
   - `frame-ancestors 'none'` (refuerzo X-Frame-Options)

### 9.3 HTTPS y Transporte Seguro

- **SSL/TLS**: PythonAnywhere con Let's Encrypt (renovación automática).
- **Redirección Forzada**: `SECURE_SSL_REDIRECT = True` en production.py.
- **HSTS**: `SECURE_HSTS_SECONDS = 31536000` (1 año), `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True` (elegible para preload list Chrome/Mozilla).
- **Cookies Seguras**: `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True` (no accesible desde JS), `SESSION_COOKIE_SAMESITE = 'Lax'`, `SESSION_COOKIE_AGE = 3600` (1 hora de inactividad).
- **Cabeceras Extra**: `SECURE_CONTENT_TYPE_NOSNIFF = True` (X-Content-Type-Options: nosniff), `X_FRAME_OPTIONS = 'DENY'` (protege Clickjacking), `REFERRER_POLICY = 'strict-origin-when-cross-origin'`.

### 9.4 RBAC (Role-Based Access Control) — 6 Roles SENA

#### Modelo de Grupos Django (no tabla custom):

| Grupo Django | Descripción | Permisos Clave |
|---|---|---|
| **Administrador** | Superusuario técnico (equipo SENA TI) | Todo: CRUD total, auditoría, backups, settings |
| **Coordinador Feria** | Responsable organizacional | Proyectos, eventos, reportes, usuarios, certificados |
| **Instructor** | Guía de proyectos | Ver/editar sus proyectos, inscripción de aprendices |
| **Aprendiz** | Participante | Ver su ficha, proyecto, escarapela, certificado |
| **Jurado** | Evaluador | Asignar calificaciones a proyectos asignados |
| **Visitante** | Invitado feria | Registro, escarapela, asistencia, feria pública |

#### Implementación:

1. **`core/mixins.py`** — `GroupRequiredMixin` hereda `LoginRequiredMixin`:
   ```python
   class GroupRequiredMixin(LoginRequiredMixin):
       group_required = []
       def dispatch(self, request, *args, **kwargs):
           if not request.user.is_authenticated: return self.handle_no_permission()
           if request.user.is_superuser: return super().dispatch(request, *args, **kwargs)
           if not request.user.groups.filter(name__in=self.group_required).exists():
               raise PermissionDenied
           return super().dispatch(request, *args, **kwargs)
   ```
2. **`core/decorators.py`** — `@require_group(['Coordinador Feria'])` para FBV.
3. **`core/constants.py`** — `GRUPOS_SENA = ['Administrador', 'Coordinador Feria', ...]` usados en migración fixture `0002_seed_groups` (usuarios app) para auto-crear grupos al instalar.
4. **Cada App**: vistas CBV usan `class ProyectoUpdateView(GroupRequiredMixin, UpdateView): group_required = ['Coordinador Feria', 'Instructor']`
5. **Templates**: `{% if perms.proyectos.change_proyecto or user|in_group:'Coordinador Feria' %}` con tag `in_group` (core/templatetags).
6. **Admin Django**: `admin.site` restringido a `is_superuser OR is_staff AND in_group 'Administrador'/'Coordinador'`.

### 9.5 Medidas Adicionales de Seguridad:

- **Administrador Oculto**: `ADMIN_URL` variable desde `.env` (ej: `/panel-sena-8374-admin/`) — nunca `/admin/`.
- **Rate Limiting**: `django-ratelimit` (agregar al stack) para endpoints de login, QR scanner, reportes.
- **Contraseñas**: `AUTH_PASSWORD_VALIDATORS` Django por defecto + longitud mínima 12 caracteres.
- **Login**: 5 intentos fallidos → bloqueo 30 min (middleware personalizado en core).
- **Subida de Archivos**: Validación MIME type + tamaño máximo (5MB por imagen), extensión whitelist [jpg, jpeg, png, pdf, xlsx], directorio `media/` NO ejecutable (cabecera `X-Content-Type-Options: nosniff`).
- **Claves Secretas**: NUNCA en `settings.py`, siempre vía `.env` → `SECRET_KEY` rotación anual, `DB_BACKUP_DIR` con permisos 600.

---

## 10. ESTRATEGIA DE CONTINGENCIA

### Nivel 1: Prevención (Evitar el Incidente)

| Medida | Frecuencia | Responsable | Valor Umbral / Descripción |
|---|---|---|---|
| `manage.py check --deploy` | Antes de cada deploy | Equipo TI | 0 errores permitidos |
| Backup completo DB + Media | Diario 2:00 AM | Script automático | Retención 14 días |
| Verificación restauración backup | Quincenal | Coordinador TI | Punto de control validado |
| `pip-audit` de dependencias | Semanal | CI/CD | 0 vulnerabilidades CRÍTICAS |
| Revisión auditoría (últimas 24h) | Diaria 9:00 AM | Administrador | Acciones anómalas reportadas |
| Monitoreo espacio en disco | Cada hora | PythonAnywhere alerts | < 1 GB libre = alerta |
| Prueba endpoints críticos (login, QR, cert) | Cada 10 min | Monitor externo | > 5s o 4xx/5xx = alerta |

### Nivel 2: Respuesta a Incidentes (Escalación)

#### Escenario A: Base de datos corrupta o pérdida de datos

1. **T0** — Confirmar incidente; **inmediatamente activar modo mantenimiento** (página estática 503 personalizada).
2. **T+5 min** — Identificar último backup íntegro (`/backups/db_YYYYMMDD_HHMM.sqlite3`).
3. **T+10 min** — Copiar backup como `db.sqlite3` nuevo (conservar el dañado renombrado como `db_corrupto_*.sqlite3` para análisis forense).
4. **T+15 min** — Ejecutar `python manage.py check` + `python manage.py migrate` + `python manage.py createsuperuser` si aplica.
5. **T+20 min** — Verificar login, dashboard, asistencia, reportes.
6. **T+25 min** — Desactivar modo mantenimiento; comunicar a Coordinador Feria.
7. **Post-incidente (24h)** — Informe RCA (Root Cause Analysis) firmado.

#### Escenario B: Caída del servicio PythonAnywhere

1. **T0** — Confirmar status.pythonanywhere.com.
2. **T+3 min** — Activar plan B local: pre-instancia local (laptop Coordinador) con último backup restaurado + Hotspot WiFi.
3. **T+5 min** — Instruir al personal de control de acceso usar registro manual físico (bitácora papel pre-impresa) para asistencia y refrigerios.
4. **T+N min** — Monitorear PythonAnywhere; al retorno: sincronizar registros manuales cargando en bulk vía `python manage.py shell`.
5. **Post-incidente** — Anotar desfases en módulo `auditoria/` con tag `[CONTINGENCIA]`.

#### Escenario C: Vulneración de seguridad (CSRF/XSS/RBAC bypass detectado)

1. **T0** — Bloquear inmediatamente: `SECURE_SSL_REDIRECT` + forzar logout todos los usuarios (`SESSION_COOKIE_AGE = 0` temporal).
2. **T+2 min** — Sacar snapshot de `db.sqlite3` + logs (evidencia forense).
3. **T+10 min** — Rotar `SECRET_KEY` en `.env` (invalida todas las sesiones y tokens firmados).
4. **T+15 min** — Revisar auditoría 72h atrás en `auditoria.RegistroAuditoria` filtrando IPs/usuarios sospechosos.
5. **T+30 min** — Actualizar dependencias `pip install --upgrade`.
6. **T+1h** — Desbloquear servicio con contraseñas rotadas a afectados (si los hay).
7. **T+48h** — Informe de seguridad + parche preventivo deployado.

### Nivel 3: Continuidad Operativa Mínima

Siempre que exista falla de energía, red o servidor, el equipo de la feria debe contar con:

- **Impresos físicos** de todas las escarapelas (24h antes).
- **Bitácoras de papel** (3 ejemplares) para: asistencia, refrigerios, evaluaciones.
- **Laptop offline** con última copia de certificados y reportes.
- **USB encriptado** (BitLocker / VeraCrypt) con último backup `db.sqlite3` + carpeta `media/` completo.
- **Teléfonos designados** (2) para comunicaciones al coordinador + TI.

---

## 11. GUÍA DE INSTALACIÓN RÁPIDA (REFERENCIA)

```bash
# 1. Clonar / Crear entorno
cd c:\Feria_2026
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Linux / Mac

# 2. Dependencias
pip install -r requirements.txt
# requirements.txt contendría:
#   Django==5.1.1
#   Pillow==10.4.0
#   qrcode==7.4.2
#   ReportLab==4.2.5
#   openpyxl==3.1.5
#   whitenoise==6.7.0
#   python-dotenv==1.0.1
#   + django-ratelimit, django-cleanup (opcionales recomendados)

# 3. Variables de entorno
# Copiar .env.example a .env y editar SECRET_KEY, etc.

# 4. Base de datos y superusuario
python manage.py migrate
python manage.py createsuperuser

# 5. Colectar estáticos
python manage.py collectstatic --noinput

# 6. Levantar servidor desarrollo
python manage.py runserver

# 7. Producción: seccion 8 de este documento
```

---

*Documento: ARQUITECTURA.md · Versión 1.0 · Fecha: 02/10/2026 · Estado: Aprobado para desarrollo*
*Sistema: Gestión Feria Proyectos Productivos SENA · Arquitectura: Django 5 Monolítico MVT*
