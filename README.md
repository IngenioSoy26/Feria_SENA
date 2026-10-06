# SENA Feria Proyectos Productivos

## Programa Articulación Media - SENA Regional Guajira

### Descripción

Sistema de información web desarrollado para la gestión, seguimiento y visualización de proyectos productivos presentados en la Feria de Proyectos Productivos del programa de Articulación con la Media Técnica de la Regional Guajira del Servicio Nacional de Aprendizaje (SENA).

El sistema permite administrar fichas, aprendices, proyectos productivos, evaluaciones, generar reportes y códigos QR para identificación de stands, así como la exportación de datos en formatos Excel y PDF.

### Stack Tecnológico

| Componente | Versión | Descripción |
|------------|---------|-------------|
| **Python** | 3.10 | Lenguaje de programación (compatible con PythonAnywhere) |
| **Django** | 5.1.2 | Framework web principal |
| **Pillow** | 10.4.0 | Procesamiento de imágenes |
| **qrcode** | 7.4.2 | Generación de códigos QR |
| **openpyxl** | 3.1.5 | Lectura y escritura de archivos Excel |
| **reportlab** | 4.2.5 | Generación de reportes PDF |
| **pandas** | 2.3.3 | Análisis y manipulación de datos |
| **python-dotenv** | 1.0.1 | Gestión de variables de entorno |
| **whitenoise** | 6.7.0 | Servicio de archivos estáticos en producción |
| **django-csp** | 3.8 | Política de Seguridad de Contenido (CSP) |
| **argon2-cffi** | 23.1.0 | Hashing seguro de contraseñas |

### Estructura de Carpetas (Resumen)

```
Feria_2026/
├── docs/                       # Documentación técnica del proyecto
│   ├── ARQUITECTURA.md         # Arquitectura del sistema
│   ├── IDENTIDAD_VISUAL_SENA.md # Guía de identidad visual
│   ├── MODELO_DATOS.md         # Modelo entidad-relación
│   └── ROLES_PERMISOS.md       # Matriz de roles y permisos
├── media/                      # Archivos subidos (imágenes, documentos)
├── staticfiles/                # Archivos estáticos recolectados (producción)
├── templates/                  # Plantillas HTML del sistema
├── apps/                       # Aplicaciones Django del proyecto
│   ├── usuarios/               # Gestión de usuarios y autenticación
│   ├── fichas/                 # Gestión de fichas de formación
│   ├── proyectos/              # Gestión de proyectos productivos
│   ├── evaluaciones/           # Sistema de evaluación de proyectos
│   └── reportes/               # Generación de reportes y exportaciones
├── core/                       # Configuración principal del proyecto Django
├── manage.py                   # Script de administración Django
├── requirements.txt            # Dependencias del proyecto
├── .env.example                # Plantilla de variables de entorno
├── .gitignore                  # Archivos ignorados por Git
└── README.md                   # Este archivo
```

---

## Guía de Instalación Local

### Paso 1: Clonar o descargar el proyecto

Clonar el repositorio desde el sistema de control de versiones:

```bash
git clone <URL_DEL_REPOSITORIO>
cd Feria_2026
```

O bien, descargar y extraer el archivo ZIP del proyecto, luego navegar al directorio raíz `Feria_2026`.

### Paso 2: Crear el entorno virtual

Ejecutar el siguiente comando en la raíz del proyecto para crear un entorno virtual de Python:

```bash
py -m venv venv
```

### Paso 3: Activar el entorno virtual

**En Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**En Windows (CMD):**
```cmd
venv\Scripts\activate.bat
```

**En Linux / macOS:**
```bash
source venv/bin/activate
```

Al activar correctamente el entorno, verás el prefijo `(venv)` al inicio de la línea de comandos.

### Paso 4: Instalar dependencias

Con el entorno virtual activado, instalar todas las dependencias del proyecto:

```bash
pip install -r requirements.txt
```

### Paso 5: Configurar variables de entorno

Copiar el archivo de plantilla de variables de entorno y configurarlo según el entorno local:

```bash
copy .env.example .env
```

Editar el archivo `.env` y cambiar los valores de acuerdo a la configuración local. Por defecto viene configurado para desarrollo local.

### Paso 6: Aplicar migraciones de la base de datos

Ejecutar las migraciones para crear la estructura de la base de datos:

```bash
python manage.py migrate
```

### Paso 7: Cargar datos de demostración (seed)

Ejecutar el comando personalizado para poblar la base de datos con datos de ejemplo:

```bash
python manage.py seed_demo
```

Este comando crea usuarios de prueba, fichas, aprendices, proyectos y evaluaciones de ejemplo.

### Paso 8: Iniciar el servidor de desarrollo

Levantar el servidor web de desarrollo de Django:

```bash
python manage.py runserver
```

Abrir en el navegador la dirección: **http://localhost:8000**

---

## Usuarios Demo

| Rol | Usuario | Contraseña | Descripción |
|-----|---------|------------|-------------|
| **Administrador** | `admin_sena` | `SenaFeria2026*` | Acceso total al sistema, panel admin: `/admin-seguro-sena-2026/` |
| **Coordinador** | `coordinador_media` | `Coordinador2026*` | Gestión global de fichas, proyectos y evaluaciones |
| **Instructor Evaluador** | `instructor_evaluador` | `Instructor2026*` | Registro y consulta de evaluaciones a proyectos |
| **Instructor Líder** | `instructor_lider` | `Lider2026*` | Gestión de su ficha y proyectos asignados |
| **Aprendiz** | `aprendiz_demo` | `Aprendiz2026*` | Consulta de información de su ficha y proyecto |

> **Nota:** Cambie estas contraseñas inmediatamente después del primer inicio de sesión en entornos de producción.

---

## Fases de Desarrollo Completadas

| Fase | Estado | Descripción |
|------|--------|-------------|
| ✅ **Fase 1: Levantamiento de Requisitos** | Completada | Entrevistas, análisis de necesidades y documentación de requisitos funcionales y no funcionales |
| ✅ **Fase 2: Diseño de Arquitectura** | Completada | Definición de arquitectura, modelo de datos, roles y permisos, e identidad visual SENA |
| ✅ **Fase 3: Modelado de Datos** | Completada | Diseño ER, creación de modelos Django y relaciones, migraciones iniciales |
| ✅ **Fase 4: Desarrollo Módulo Usuarios** | Completada | Autenticación, gestión de usuarios, roles, permisos y recuperación de contraseñas |
| ✅ **Fase 5: Desarrollo Módulo Fichas y Aprendices** | Completada | CRUD de fichas, aprendices, importación desde Excel y asociación a instructores |
| ✅ **Fase 6: Desarrollo Módulo Proyectos** | Completada | Registro de proyectos productivos, categorías, stands, archivos adjuntos y códigos QR |
| ✅ **Fase 7: Desarrollo Módulo Evaluaciones** | Completada | Formularios de evaluación, rúbricas, asignación de evaluadores y calificaciones |
| ✅ **Fase 8: Desarrollo Módulo Reportes** | Completada | Tablero de indicadores, exportación Excel/PDF, estadísticas y gráficos |
| ✅ **Fase 9: Seguridad y Optimización** | Completada | CSP, hashing Argon2, validaciones, auditoría y optimización de consultas |
| ✅ **Fase 10: Pruebas y Datos Demo** | Completada | Comando `seed_demo`, pruebas de integración y documentación de usuarios de prueba |
| ⚙️ **Fase 11: Despliegue a Producción** | En curso | Configuración para PythonAnywhere, variables de entorno, archivos estáticos/media |

---

## Enlaces a Documentación Técnica

- 📘 [Arquitectura del Sistema](docs/ARQUITECTURA.md) - Visión general, diagramas y decisiones de diseño
- 🎨 [Identidad Visual SENA](docs/IDENTIDAD_VISUAL_SENA.md) - Paleta de colores, tipografía y lineamientos gráficos
- 🗃️ [Modelo de Datos](docs/MODELO_DATOS.md) - Diagrama ER, descripción de entidades y relaciones
- 🔐 [Roles y Permisos](docs/ROLES_PERMISOS.md) - Matriz de roles, permisos y funcionalidades por perfil
