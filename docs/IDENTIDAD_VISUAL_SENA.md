# MANUAL DE IDENTIDAD VISUAL - SISTEMA FERIA PROYECTOS PRODUCTIVOS SENA

> Basado en el Manual de Identidad Visual SENA 2024  
> Versión: 1.0 — Octubre 2026  
> Aplicable a: Sistema Web, Dashboard, PWA, PDF (Escarapelas y Certificados), UI Institucional

---

## 1. COLOR INSTITUCIONAL PRINCIPAL

### 1.1 Verde SENA (Color Corporativo)

| Propiedad | Valor |
|-----------|-------|
| Hex | `#39A900` |
| RGB | `rgb(57, 169, 0)` |
| HSL | `hsl(100, 100%, 33%)` |
| CMYK | `66, 0, 100, 34` |
| Uso | Fondos de barra superior, botones primarios, acentos, marcas de verificación, estados correctos, logo institucional |

```css
:root {
  --sena-green: #39A900;
  --sena-green-hover: #309100;
  --sena-green-active: #287A00;
  --sena-green-light: rgba(57, 169, 0, 0.08);
  --sena-green-border: rgba(57, 169, 0, 0.25);
}
```

---

## 2. PALETA COMPLEMENTARIA — NEUTROS

| Nombre | Hex | RGB | Uso |
|--------|-----|-----|-----|
| **Blanco** | `#FFFFFF` | `255, 255, 255` | Fondo principal de página, fondo de tarjetas, texto sobre verde SENA |
| **Gris Claro** | `#F5F5F5` | `245, 245, 245` | Fondo secundario, fondos de campos deshabilitados, separadores sutiles |
| **Gris Medio** | `#9E9E9E` | `158, 158, 158` | Texto secundario, placeholders, iconos no activos, bordes deshabilitados |
| **Gris Oscuro** | `#424242` | `66, 66, 66` | Texto cuerpo principal, subtítulos, etiquetas de formulario |
| **Negro** | `#212121` | `33, 33, 33` | Títulos, encabezados de tabla, textos de alto énfasis |

```css
:root {
  --sena-white:  #FFFFFF;
  --sena-gray-50:  #F5F5F5;
  --sena-gray-500: #9E9E9E;
  --sena-gray-800: #424242;
  --sena-black: #212121;
}
```

### 2.1 Jerarquía Tipográfica de Colores

```
Título / H1 → #212121 (Negro)  — peso 700
Subtítulo / H2-H3 → #424242 (Gris Oscuro) — peso 600
Texto cuerpo → #424242 (Gris Oscuro) — peso 400
Texto secundario / metadatos → #9E9E9E (Gris Medio) — peso 400
Placeholder → #9E9E9E (Gris Medio)
Texto sobre fondo verde SENA → #FFFFFF (Blanco)
```

---

## 3. TIPOGRAFÍA

### 3.1 Familia Tipográfica Principal

**Work Sans** — Tipografía oficial del SENA 2024

- Origen: Google Fonts (SIL Open Font License)
- Uso: Títulos, subtítulos, botones, navegación, encabezados, UI en general
- Pesos recomendados: 400 (Regular), 500 (Medium), 600 (SemiBold), 700 (Bold)
- Evitar: Light (300) en tamaños menores de 16px por legibilidad

```css
@import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;500;600;700&display=swap');

:root {
  --font-primary: 'Work Sans', system-ui, -apple-system, sans-serif;
  --font-secondary: Calibri, 'Segoe UI', sans-serif;
}

html, body {
  font-family: var(--font-primary);
  color: var(--sena-gray-800);
  -webkit-font-smoothing: antialiased;
}
```

### 3.2 Familia Tipográfica Secundaria

**Calibri** — Complementaria para documentos formales y PDF

- Uso: Cuerpo extenso en certificados PDF, escarapelas, texto narrativo de informes
- Cuando Work Sans no está disponible en documentos renderizados offline, Calibri sustituye como fallback seguro en entornos Windows

### 3.3 Escala Modular Tipográfica (Mobile First)

| Elemento | Móvil (< 768px) | Tablet / Desktop | Peso | Línea |
|----------|------------------|------------------|------|-------|
| H1 — Título principal | 24px / 1.5rem | 32px / 2rem | 700 | 1.2 |
| H2 — Sección | 20px / 1.25rem | 26px / 1.625rem | 600 | 1.3 |
| H3 — Subsección | 18px / 1.125rem | 22px / 1.375rem | 600 | 1.3 |
| Cuerpo (p) | 16px / 1rem | 16px / 1rem | 400 | 1.6 |
| Texto pequeño | 14px / 0.875rem | 14px / 0.875rem | 400 | 1.5 |
| Etiqueta / Help text | 12px / 0.75rem | 12px / 0.75rem | 500 | 1.4 |
| Botones | 16px / 1rem | 16px / 1rem | 600 | 1 |

> Mínimo tamaño de fuente accesible: 14px (WCAG AA). Ningún texto funcional por debajo de 12px.

---

## 4. LOGOSÍMBOLO SENA — REGLAS DE USO

### 4.1 Prohibiciones Absolutas

| Regla | Descripción |
|-------|-------------|
| ❌ No deformar | Mantener proporción original (aspect ratio fijo). Nunca estirar en X o Y independientemente |
| ❌ No rotar | Siempre en posición horizontal 0°. Ningún ángulo ni inclinación |
| ❌ No sombras | El logotipo no lleva drop-shadow, box-shadow ni text-shadow de ningún tipo |
| ❌ No degradados | Colores planos sólidos únicamente. Sin gradientes lineales, radiales ni mallas |
| ❌ No cambiar colores | Versiones permitidas: (a) Verde SENA #39A900 sobre fondo claro, (b) Blanco #FFFFFF sobre fondo verde SENA o oscuro, (c) Negro #212121 monocromático para impresión |
| ❌ No contornos ni trazos | No rellenar solo con borde. Siempre sólido |
| ❌ No superponer | No colocar el logo sobre fotografías, patrones o fondos con texto que dificulten su lectura |

### 4.2 Área de Seguridad (Zona de Respeto)

El área de seguridad equivale a **1× la altura de la "S" del logosímbolo** en los cuatro lados (arriba, abajo, izquierda, derecha).

```
┌───────────────────────────────┐
│   ↕ Zona seguridad (altura S) │
│   ┌───────────────────────┐   │
│ ↔ │                       │ ↔ │
│   │    LOGOSÍMBOLO SENA   │   │
│   │                       │   │
│   └───────────────────────┘   │
│   ↕ Zona seguridad (altura S) │
└───────────────────────────────┘
```

En código CSS:

```css
.sena-logo {
  display: inline-block;
  aspect-ratio: 5 / 1; /* ratio del logosímbolo oficial */
  padding: var(--logo-safezone);
}
.sena-logo img { width: 100%; height: 100%; object-fit: contain; }
```

### 4.3 Tamaños Mínimos

| Soporte | Tamaño mínimo (ancho) | Tamaño mínimo (altura) |
|---------|------------------------|-------------------------|
| Web / App (pantalla) | 120px | 24px |
| PDF Certificado (impresión) | 40mm ≈ 150px | 8mm ≈ 30px |
| PDF Escarapela | 25mm ≈ 95px | 5mm ≈ 19px |
| Favicon / PWA 16px | — | 16px (versión simplificada solo símbolo) |
| PWA 192×192 y 512×512 | — | 512px (simbolo + texto si aplica) |

### 4.4 Uso Correcto del Logo — Casillas de Verificación

| Contexto | Color de fondo | Color de logo | Ejemplo de uso |
|----------|----------------|---------------|----------------|
| Header (barra superior) | Verde SENA `#39A900` | Blanco `#FFFFFF` | Logo completo alineado a la izquierda |
| Dashboard (fondo claro) | Blanco `#FFFFFF` o Gris Claro `#F5F5F5` | Verde SENA `#39A900` | Logo completo o símbolo en sidebar |
| Footer PDF | Blanco | Verde SENA | Logo completo alineado derecha + Nombre Centro |
| Portada Certificado | Blanco | Verde SENA + Negro para tipografía institucional | Logo en esquina superior izquierda |
| Loading / Splash PWA | Verde SENA | Blanco | Logosímbolo centrado animado fade-in |

---

## 5. ESTADOS OPERATIVOS SEMÁNTICOS

Los estados VERDE, AMARILLO y ROJO se definen como paleta de **acento semántico** de apoyo, sin reemplazar nunca al Verde SENA institucional como color principal del sistema.

### 5.1 Definición

| Estado | Color Hex | RGB | Significado Operativo |
|--------|-----------|-----|-----------------------|
| 🟢 **VERDE — Correcto / OK** | `#2E7D32` | `46, 125, 50` | Registro exitoso, validación aprobada, inscripción completada sin errores, check-in confirmado |
| 🟡 **AMARILLO — Duplicado / Advertencia** | `#F9A825` | `249, 168, 37` | Registro duplicado detectado, ficha con inconsistencia leve, advertencia antes de guardar, acción requiere confirmación |
| 🔴 **ROJO — Error / Rechazado** | `#C62828` | `198, 40, 40` | Error de validación, documento inválido, fallo de conexión, operación rechazada, duplicado grave |

```css
:root {
  --status-success:  #2E7D32;
  --status-success-bg:  rgba(46, 125, 50, 0.10);
  --status-warning:  #F9A825;
  --status-warning-bg:  rgba(249, 168, 37, 0.12);
  --status-danger:   #C62828;
  --status-danger-bg:   rgba(198, 40, 40, 0.10);
}
```

### 5.2 Compatibilidad con la Identidad SENA

- El `VERDE OK (#2E7D32)` es un verde más oscuro que el Verde SENA. Debe usarse **solo** como indicador de estado (badge, chip, borde), nunca como color de marca o de botón principal.
- El botón primario de la aplicación sigue siendo `#39A900` (Verde SENA).
- Cuando un estado de éxito necesite un botón (p. ej., "Confirmar asistencia"), se usa Verde SENA, y el badge de estado usa Verde Correcto.
- Amarillo y Rojo no modifican tipografía ni espaciado: solo fondo, borde y símbolo.

### 5.3 Uso en Badges y Chips

```html
<!-- Correcto -->
<span class="badge badge-success">
  <span class="dot"></span> INSCRIPCIÓN OK
</span>

<!-- Duplicado / Advertencia -->
<span class="badge badge-warning">
  <span class="dot"></span> FICHA DUPLICADA
</span>

<!-- Error -->
<span class="badge badge-danger">
  <span class="dot"></span> CÉDULA NO VÁLIDA
</span>
```

```css
.badge {
  display: inline-flex; align-items: center; gap: .5rem;
  padding: .4rem .75rem; border-radius: 999px;
  font-size: .8rem; font-weight: 600; letter-spacing: .3px;
}
.badge .dot { width: .55rem; height: .55rem; border-radius: 50%; }

.badge-success { background: var(--status-success-bg); color: var(--status-success);}
.badge-success .dot { background: var(--status-success); }

.badge-warning { background: var(--status-warning-bg); color: #7a5400;}
.badge-warning .dot { background: var(--status-warning); }

.badge-danger  { background: var(--status-danger-bg); color: var(--status-danger);}
.badge-danger  .dot { background: var(--status-danger); }
```

---

## 6. DISEÑO DE ESCARAPELAS PDF

### 6.1 Especificaciones Técnicas

| Propiedad | Valor |
|-----------|-------|
| Tamaño página | **A6 horizontal** — 148 mm × 105 mm (5.83" × 4.13") |
| Margen interno de seguridad | 8 mm en cada lado |
| Orientación | Horizontal / Paisaje |
| Resolución fuente | ≥ 300 DPI (imágenes del logo incrustado en PNG 300dpi o vector SVG) |
| Color | CMYK para imprenta; RGB OK para visualización digital |
| Formato de entrega | PDF /A-1b o PDF 1.4 (accesible) |

### 6.2 Composición Visual

```
┌───────────────────────────────────────────────────────┐
│  ┌───┐  LOGO SENA (Blanco)                            │ ← Banda Verde SENA #39A900
│  │sim│  SERVICIO NACIONAL DE APRENDIZAJE              │   Altura 22mm
│  └───┘  FERIA PROYECTOS PRODUCTIVOS 2026              │
├───────────────────────────────────────────────────────┤
│                                                       │
│   [ Foto 30x40mm ]   NOMBRE COMPLETO DEL APRENDIZ     │
│                      (Work Sans 700, 14pt, #212121)   │
│                                                       │
│                      Ficha: 1234567                   │
│                      Programa: Técnico en...          │
│                      Centro de Formación ...          │
│                       (Work Sans 400, 9pt, #424242)   │
│                                                       │
│   [QR]                                                │
│   QR Asistencia     CATEGORÍA                         │
│                      ┌────────────┐                   │
│                      │ APRENDIZ   │ ← Badge Verde SENA│
│                      └────────────┘                   │
├───────────────────────────────────────────────────────┤
│  www.sena.edu.co  ·  2026  ·  Centro de Formación     │ ← Pie #F5F5F5
└───────────────────────────────────────────────────────┘
```

### 6.3 Tipos de Escarapela por Rol / Categoría

| Categoría | Etiqueta visual | Color de badge |
|-----------|-----------------|----------------|
| APRENDIZ | Rectángulo esquinas redondeadas (radius 4px) | Verde SENA `#39A900` + texto blanco |
| INSTRUCTOR | Idem | Gris Oscuro `#424242` + texto blanco |
| EVALUADOR | Idem | Negro `#212121` + texto blanco |
| ADMINISTRADOR / ORGANIZADOR | Idem | Borde Verde SENA + fondo blanco + texto `#39A900` |
| VISITANTE | Idem | Gris Medio `#9E9E9E` + texto blanco |

### 6.4 Reglas Impresión

- **Nunca** imprimir la escarapela a doble cara del mismo pliego; usar siempre portador de PVC reutilizable o carnet plastificado.
- Código QR: siempre con zona blanca de silencio (quiet zone) de 4mm alrededor. Tamaño mínimo QR: 25mm × 25mm.
- Nivel de corrección QR: **Q** (25%) para tolerar dobleces y plastificado.

---

## 7. DISEÑO DE CERTIFICADOS PDF

### 7.1 Especificaciones Técnicas

| Propiedad | Valor |
|-----------|-------|
| Tamaño página | **Oficio (Legal)** 216 mm × 356 mm o **A4** 210 mm × 297 mm según normativa del centro |
| Orientación | Vertical / Retrato |
| Márgenes | Superior 25mm, Inferior 25mm, Laterales 20mm |
| Tipografía título | Work Sans 700 |
| Tipografía cuerpo | Work Sans 400 (primaria) / Calibri 400 (fallback PDF) |
| Resolución | ≥ 300 DPI en imágenes incrustadas |

### 7.2 Composición — Portada / Frente Único

```
╔═══════════════════════════════════════════════════════╗
║  ┌───┐                                                ║
║  │ S │  SERVICIO NACIONAL DE APRENDIZAJE              ║  ← Banda superior:
║  │ENA│  REPÚBLICA DE COLOMBIA                         ║    Logo SENA verde +
║  └───┘                                                ║    Tipografía institucional
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║                C E R T I F I C A D O                  ║  ← 28pt, #212121, 700
║                                                       ║
║  El Centro de Formación [Nombre Centro] certifica     ║  ← Calibri 12pt, justificado
║  que __________________________________ identificado  ║
║  con C.C. / T.I. ___________ de la Ficha N° _______   ║
║  participó en la FERIA DE PROYECTOS PRODUCTIVOS       ║
║  2026 con el proyecto titulado:                       ║
║                                                       ║
║          "TÍTULO DEL PROYECTO EN MAYÚSCULAS"          ║  ← 14pt, #39A900, 600
║                                                       ║
║  bajo la modalidad ________________________________,  ║
║  obteniendo la calificación: ________________________ ║
║  obteniendo el puesto: ______________________________ ║
║                                                       ║
║  Se expide en ____________ a los ___ días del mes de  ║
║  ____________ de 2026.                                ║
║                                                       ║
║                                                       ║
║                       ───────────                     ║
║                       FIRMA DEL (LA) DIRECTOR(A)      ║
║                       Centro de Formación SENA        ║
║                                                       ║
║  ──── VALIDACIÓN DIGITAL ────                         ║
║  Código único: FPP-2026-XXXXXXX                       ║
║  [QR 35×35]  →   Verifique en sena.edu.co/feria2026   ║
╠═══════════════════════════════════════════════════════╣
║  Franja inferior #39A900 altura 15mm                  ║
║  Texto blanco: FERIA PROYECTOS PRODUCTIVOS 2026       ║
║  ·  www.sena.edu.co  ·  Contáctenos                  ║
╚═══════════════════════════════════════════════════════╝
```

### 7.3 Jerarquía de Información en Certificados

1. **Zona institucional (Top):** Logo SENA + Nombre oficial (15-18pt, Work Sans 600, #212121)
2. **Título documento:** "CERTIFICADO" (26-32pt, Work Sans 700, #212121 — tracking 4pt)
3. **Texto declarativo:** Cuerpo Calibri 11-12pt, color #424242, justificado
4. **Datos variables resaltados:** Nombre, Título del Proyecto en Verde SENA `#39A900` y/o negrita
5. **Firma:** Nombre + cargo — Work Sans 600 11pt, #212121
6. **Banda pie:** Franja completa Verde SENA, texto blanco Work Sans 10pt

### 7.4 Accesibilidad PDF

- Etiquetado estructural (PDF/UA): `<H1>` = CERTIFICADO, `<P>` = párrafos
- Idioma declarado: `es-CO`
- Marcado de lectura para lectores de pantalla en orden: Logo → Título → Cuerpo → Firma → Pie
- Texto mínimo 10pt

---

## 8. DISEÑO DASHBOARD — MOBILE FIRST

### 8.1 Principio Mobile First

Todo diseño de interfaz se **diseña, prototipa y prueba primero en viewport móvil 360×640 (Galaxy A-class / iPhone SE)** y luego escala hacia tablet (768px) y desktop (≥1200px).

| Breakpoint | Nombre | Ancho mínimo | Patrón de navegación |
|------------|--------|--------------|----------------------|
| ≥ 0px | Base — Móvil | — | Navegación inferior (Bottom Navigation) de 5 botones máx. |
| ≥ 768px | Tablet | 768px | Sidebar vertical contraíble + Breadcrumb |
| ≥ 1200px | Desktop | 1200px | Sidebar expandida con iconos + texto, 2/3 columnas |

### 8.2 Layout Base — Móvil

```
┌──────────────────────────────┐
│ ← LOGO SENA blanco    [perfil] │ ← AppBar #39A900 (h: 56px)
├──────────────────────────────┤
│                              │
│  [Tarjeta métrica 1]         │ ← Cards con border-radius 12px
│  Total fichas: 1,248         │   sombra sutil (0 2px 8px rgba(0,0,0,0.06))
│  Verde  ● 980                │
│  Amarilla ● 187              │
│  Roja   ● 81                 │
│                              │
│  [Tarjeta métrica 2]         │
│  Registro hoy               │
│  + 124                       │
│                              │
│  ┌────────────────────────┐  │
│  │  🔎 Buscar aprendices   │  │ ← Searchbar alto 48px mínimo
│  └────────────────────────┘  │
│                              │
│  [ Chip: Todos | Hoy | Sem. ]│ ← Chips filtro
│                              │
│  ┌────────────────────────┐  │
│  │  Lista fichas / tabla  │  │ ← Filas ≥ 52px alto táctil
│  │  Pérez Gómez, Juan     │  │
│  │  Ficha 1234567   [🟢]  │  │
│  └────────────────────────┘  │
│                              │
│                              │ ← Espacio bottom nav
├──────────────────────────────┤
│ 🏠  📋  ✅  👥  ⚙️            │ ← Bottom Nav #FFFFFF,
│ Inicio List Check Perfil Ajus│   active: icono + label en Verde SENA
└──────────────────────────────┘
```

### 8.3 Sistema de Espaciado

Usar escala 4px (multiplos de 4) predecible y consistente:

```css
:root {
  --space-1: .25rem;   /* 4px  */
  --space-2: .5rem;    /* 8px  */
  --space-3: .75rem;   /* 12px */
  --space-4: 1rem;     /* 16px */
  --space-5: 1.5rem;   /* 24px */
  --space-6: 2rem;     /* 32px */
  --space-8: 3rem;     /* 48px */
}
```

Padding de tarjetas en móvil: `1.25rem (20px)`; padding lateral de pantalla: `1rem (16px)`; separación entre tarjetas: `1rem`.

### 8.4 Targetas (Cards)

```css
.card {
  background: var(--sena-white);
  border: 1px solid rgba(0,0,0,0.06);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  padding: var(--space-5);
}
```

- Ninguna sombra excesiva. Evitar bordes múltiples.
- Radio de esquina entre 8px y 16px (12px estándar). Nunca 0 ni 24+ en UI.

---

## 9. INTERFAZ INSTITUCIONAL: LIMPIA, PROFESIONAL, ACCESIBLE, RESPONSIVE

### 9.1 Principios de Limpieza Visual

1. **Máximo 2 tipografías** (Work Sans + Calibri) y 3 pesos por pantalla.
2. **Máximo 4 colores por pantalla** (Verde SENA + 3 neutros), más los 3 semánticos solo donde haya estado.
3. **Un solo CTA (Llamado a la acción) primario por pantalla** — usar botón Verde SENA; los demás botones son secundarios (outline o ghost).
4. **Sin ornamentos** (sin patrones, sin texturas, sin iconografía decorativa). Solo iconos funcionales Material Symbols o FontAwesome Outline.
5. **Alineación invisible** — elementos siempre alineados a rejilla (grid 12 columnas en desktop, 4 en móvil).

### 9.2 Botones — Grandes para Celular

| Tipo | Fondo | Texto | Borde | Tamaño mínimo táctil |
|------|-------|-------|-------|----------------------|
| **Primario** | Verde SENA `#39A900` | Blanco `#FFFFFF` | 0 | Alto ≥ 48px, Ancho ≥ 96px, padding ≥ 12px 20px |
| Secundario | Blanco `#FFFFFF` | Verde SENA `#39A900` | 1.5px #39A900 | 48×96px |
| Terciario (Ghost) | Transparente | Gris Oscuro `#424242` | 0 | 44px alto |
| Peligro | Blanco `#FFFFFF` | Rojo `#C62828` | 1.5px #C62828 | 48px alto |
| Deshabilitado | Gris Claro `#F5F5F5` | Gris Medio `#9E9E9E` | 0 | No clickeable |

```css
.btn {
  display: inline-flex; align-items: center; justify-content: center;
  min-height: 48px; padding: 12px 20px;
  border-radius: 10px; font-weight: 600; font-size: 1rem;
  transition: background .15s ease, transform .05s ease;
  cursor: pointer; border: none; gap: .5rem;
  text-decoration: none;
}
.btn-primary  { background: var(--sena-green); color: #fff; }
.btn-primary:hover  { background: var(--sena-green-hover); }
.btn-primary:active { background: var(--sena-green-active); transform: scale(.98); }

.btn-outline  { background: #fff; color: var(--sena-green);
                border: 1.5px solid var(--sena-green); }
.btn-outline:hover { background: var(--sena-green-light); }

.btn-danger   { background: #fff; color: var(--status-danger);
                border: 1.5px solid var(--status-danger); }

.btn:disabled, .btn[aria-disabled="true"] {
  background: var(--sena-gray-50); color: var(--sena-gray-500);
  border-color: transparent; cursor: not-allowed; pointer-events: none;
}
```

> **Zonas táctiles (touch targets):** todos los elementos interactivos (botones, inputs, enlaces, chips, celdas clickeables, checkbox, radio) deben tener tamaño **mínimo 48×48 px** con al menos 8px de separación entre sí (W3C Mobile Accessibility / Material Design 3).

### 9.3 Formularios

- **Label arriba** (no flotante) — Work Sans 500, 14px, color #424242
- **Altura input ≥ 48px** — padding 14px 16px, border-radius 10px, border 1px #D8D8D8 (intermedio)
- **Focus:** borde Verde SENA 2px + `outline: 2px solid rgba(57,169,0,.2)` (anillo de enfoque accesible)
- **Error:** borde 1.5px Rojo + helper text rojo + icono ⚠
- **Success:** borde 1.5px Verde Correcto + icono ✓

```css
.form-field { display: flex; flex-direction: column; gap: .35rem; margin-bottom: 1rem; }
.form-label { font-size: .875rem; font-weight: 500; color: var(--sena-gray-800); }
.form-input {
  min-height: 48px; padding: 0 16px;
  border: 1px solid #D8D8D8; border-radius: 10px;
  font-size: 1rem; color: var(--sena-black); background: #fff;
}
.form-input:focus {
  outline: none; border-color: var(--sena-green);
  box-shadow: 0 0 0 3px var(--sena-green-light);
}
.form-input[aria-invalid="true"] {
  border-color: var(--status-danger);
  box-shadow: 0 0 0 3px var(--status-danger-bg);
}
.form-help { font-size: .75rem; color: var(--sena-gray-500); }
.form-error { font-size: .75rem; color: var(--status-danger); font-weight: 500; }
```

### 9.4 Alto Contraste y Accesibilidad (WCAG 2.1 AA)

| Verificación | Valor requerido | Cumplimiento SENA |
|--------------|-----------------|-------------------|
| Texto normal ≥ 16px | Ratio ≥ 4.5:1 | `#212121` sobre `#FFFFFF` = 18.4:1 ✅ |
| Texto sobre Verde SENA (blanco) | Ratio ≥ 4.5:1 | `#FFFFFF` sobre `#39A900` = 4.78:1 ✅ |
| Texto grande (≥18pt bold) | Ratio ≥ 3:1 | Garantizado con la paleta |
| Verde Correcto sobre fondo | ≥ 4.5:1 | `#2E7D32`/#FFF = 6.3:1 ✅ |
| Rojo sobre fondo | ≥ 4.5:1 | `#C62828`/#FFF = 5.4:1 ✅ |
| Amarillo sobre fondo negro | ≥ 4.5:1 | `#F9A825`/#212121 = 9.1:1. **Nunca** escribir texto oscuro sobre amarillo sobre blanco (2.7:1 ❌) |
| Enfoque visible | Focus ring de 3px | `box-shadow 0 0 0 3px rgba(57,169,0,.22)` + borde verde |

**Herramienta de verificación online recomendada:** [coolors.co/contrast-checker](https://coolors.co/contrast-checker) o WebAIM Contrast Checker.

### 9.5 Iconografía Funcional

- Familia: Material Symbols Rounded o Material Icons Outlined (preferir la variante **Rounded** por estética limpia e institucional).
- Tamaño: 20px (contenido) / 24px (botones, nav)
- Color: por defecto `#424242`; activo `#39A900`; deshabilitado `#9E9E9E`.
- Nunca usar iconos como único indicador visual; acompañar de texto aria-label y preferiblemente label visible en botones.

```html
<!-- Botón con icono + texto (recomendado) -->
<button class="btn btn-primary">
  <span class="material-symbols-rounded">check_circle</span>
  Confirmar Asistencia
</button>
```

---

## 10. PWA — PROGRESSIVE WEB APP — ICONOS Y MANIFIESTO

### 10.1 Archivos Requeridos

Ruta base dentro de proyecto: `/public/icons/`

| Archivo | Tamaño | Propósito | Formato |
|---------|--------|-----------|---------|
| `favicon.ico` | 16×16, 32×32, 48×48 embebidos | Navegador legacy (IE/Edge viejo) | ICO |
| `favicon-32.png` | 32×32 | Pestaña navegador | PNG transparente |
| `favicon-16.png` | 16×16 | Pestaña navegador (legacy) | PNG |
| `android-chrome-192x192.png` | 192×192 | Icono instalación PWA Android / Chrome | PNG |
| `android-chrome-512x512.png` | 512×512 | Splash + Play Store | PNG |
| `maskable-icon-192.png` | 192×192, con safe-zone 10% interior | Android 11+ formas adaptativas | PNG |
| `maskable-icon-512.png` | 512×512, safe-zone 10% | Ícono máscara adaptable | PNG |
| `apple-touch-icon.png` | 180×180 | iOS home screen | PNG (fondo **no** transparente) |
| `mstile-150x150.png` | 150×150 | Windows Pin | PNG |

### 10.2 Diseño del Ícono PWA

```
Composición — Fondo: Verde SENA #39A900 sólido
Simbolo central: Símbolo SENA blanco (solo la S + elementos) — NO el logo completo con texto
Área segura (safe-zone maskable): 10% margen interno para Android maskable
Forma: Exportar cuadrado 1:1. El SO se encarga del mascarilla (círculo, cuadrado, gota, etc.)
Nunca exportar el ícono con fondo transparente en iOS → fondo sólido verde SENA
```

### 10.3 Manifiesto PWA — `manifest.webmanifest` (valores)

```json
{
  "name": "Feria Proyectos Productivos SENA",
  "short_name": "Feria SENA",
  "description": "Sistema de registro y control Feria Proyectos Productivos SENA 2026",
  "lang": "es-CO",
  "dir": "ltr",
  "start_url": "/dashboard",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait-primary",
  "background_color": "#FFFFFF",
  "theme_color": "#39A900",
  "icons": [
    { "src": "/icons/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/icons/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/icons/maskable-icon-192.png",   "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/icons/maskable-icon-512.png",   "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "categories": ["business", "productivity", "education"],
  "shortcuts": [
    { "name": "Registrar asistencia", "url": "/check-in", "icons": [{ "src": "/icons/shortcut-checkin.png", "sizes": "96x96" }] },
    { "name": "Nueva ficha",         "url": "/fichas/nuevo", "icons": [{ "src": "/icons/shortcut-new.png",     "sizes": "96x96" }] }
  ]
}
```

### 10.4 Metaetiquetas HTML Obligatorias

```html
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Feria Proyectos Productivos SENA</title>
  <meta name="theme-color" content="#39A900">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="Feria SENA">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="msapplication-TileColor" content="#39A900">
  <meta name="description" content="Sistema de registro y control Feria Proyectos Productivos SENA 2026">

  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/icons/favicon-16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png">
</head>
```

### 10.5 Splash Screen PWA

- **Fondo:** Verde SENA `#39A900` sólido
- **Logo centrado:** Logosímbolo SENA completo en blanco `#FFFFFF`
- **Tipografía opcional bajo logo:** "Feria Proyectos Productivos 2026" — Work Sans 500, blanco
- **Transición:** fade-in 300ms → duración 1200ms → fade-out 200ms al cargar shell app
- Generación automática: `pwa-asset-generator` (NPM) acepta SVG de logo y genera todos los tamaños iOS splash

---

## 11. RESUMEN EJECUTIVO — CHECKLIST DE IMPLEMENTACIÓN

### 11.1 Antes de salir a producción

- [ ] **Colores:** `#39A900` Verde SENA como único verde institucional de marca; paleta neutros `#FFFFFF / #F5F5F5 / #9E9E9E / #424242 / #212121`
- [ ] **Fuentes:** `Work Sans 400/500/600/700` cargada desde Google Fonts con fallback seguro
- [ ] **Logosímbolo:** Archivo SVG original (vectorial) para web, PNG 300dpi para PDF; ninguna deformación, rotación, sombra ni degradado
- [ ] **Área de seguridad logo:** Respetada en header, footer, PDF certificados y escarapelas
- [ ] **Estados operativos:** `VERDE #2E7D32` / `AMARILLO #F9A825` / `ROJO #C62828` solo como semántica, nunca reemplazan Verde SENA en CTA
- [ ] **Tamaños táctiles:** Botones, inputs, chips ≥ 48×48px; separación entre elementos ≥ 8px
- [ ] **Contraste WCAG AA:** Todos los pares texto/fondo verificados ≥ 4.5:1
- [ ] **Focus ring visible** en todos los elementos interactivos
- [ ] **Mobile First:** UI probada en 360×640px sin scroll horizontal ni textos truncados críticos
- [ ] **Responsive:** Breakpoints 768 / 1200 con patrones nav adecuados
- [ ] **PWA:** manifest completo + 9 íconos + theme_color + apple-touch + service worker
- [ ] **PDF Escarapela (A6 horizontal):** Banda verde SENA, foto, QR, badge categoría
- [ ] **PDF Certificado (A4 / Oficio):** Logo oficial, banda inferior verde, QR validación, fuentes vectoriales embebidas
- [ ] **Idioma atributos:** `lang="es-CO"` en `<html>`, PDFs etiquetados es-CO

---

**Fin del documento — Identidad Visual Sistema Feria Proyectos Productivos SENA.**  
Cualquier modificación a esta guía debe aprobarse por Coordinación de Comunicaciones del Centro de Formación o instancia nacional de marca SENA.
