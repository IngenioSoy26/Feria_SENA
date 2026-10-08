import hashlib
import io
import re
from datetime import date

from django.db import models, transaction

from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Alignment


MESES_ES = {
    'ENERO': 1, 'FEBRERO': 2, 'MARZO': 3, 'ABRIL': 4, 'MAYO': 5, 'JUNIO': 6,
    'JULIO': 7, 'AGOSTO': 8, 'SEPTIEMBRE': 9, 'OCTUBRE': 10, 'NOVIEMBRE': 11, 'DICIEMBRE': 12,
}

TIPOS_IMPORTACION = [
    'instituciones',
    'programas',
    'instructores',
    'fichas',
    'proyectos',
    'participantes',
]

CLASIFICACION_VALIDO = 'VALIDO'
CLASIFICACION_ADVERTENCIA = 'ADVERTENCIA'
CLASIFICACION_ERROR = 'ERROR'
CLASIFICACION_DUPLICADO = 'DUPLICADO'

CLASIFICACIONES = [
    CLASIFICACION_VALIDO,
    CLASIFICACION_ADVERTENCIA,
    CLASIFICACION_ERROR,
    CLASIFICACION_DUPLICADO,
]

EMAIL_REGEX = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
FICHA_NUMERO_REGEX = re.compile(r'^\d{7}$')

MAPEO_HEADERS = {
    'instituciones': {
        'id': 'codigo',
        'instituciones_educativas': 'nombre',
        'institucion': 'nombre',
        'institucion_educativa': 'nombre',
        'ie': 'nombre',
        'colegio': 'nombre',
        'nombre_ie': 'nombre',
        'municipio': 'municipio',
        'secretaria': 'secretaria_educacion',
        'secretaria_educacion': 'secretaria_educacion',
        'secretaria_de_educacion': 'secretaria_educacion',
        'tipo': 'tipo',
        'zona': 'zona',
        'sector': 'sector',
        'caracter': 'caracter',
        'especialidad': 'especialidad',
        'direccion_i.e': 'direccion',
        'direccion': 'direccion',
        'correo_i.e': 'correo_institucional',
        'correo': 'correo_institucional',
        'correo_ie': 'correo_institucional',
        'correo_institucional': 'correo_institucional',
        'email': 'correo_institucional',
        'telefono': 'telefono',
        'telefono_ie': 'telefono',
        'telefono_institucional': 'telefono',
        'rector': 'nombre_rector',
        'celular_/_telefono': 'telefono_rector',
        'coordinador/contacto': 'nombre_coordinador',
        'celular': 'celular_coordinador',
    },
    'programas': {
        'programa': 'nombre',
        'nombre_programa': 'nombre',
        'nombre': 'nombre',
        'programas': 'nombre',
        'programa_tecnico': 'nombre',
        'codigo': 'codigo',
        'codigo_programa': 'codigo',
        'duracion': 'duracion_meses',
        'duracion_meses': 'duracion_meses',
        'descripcion': 'descripcion',
        'sector': 'sector',
    },
    'instructores': {
        'id': 'numero_identificacion',
        'cedula': 'numero_identificacion',
        'numero_identificacion': 'numero_identificacion',
        'numero_de_identificacion': 'numero_identificacion',
        'identificacion': 'numero_identificacion',
        'documento': 'numero_identificacion',
        'tipo_id': 'tipo_identificacion_cod',
        'tipo_identificacion': 'tipo_identificacion_cod',
        'tipo_de_identificacion': 'tipo_identificacion_cod',
        'tipo_documento': 'tipo_identificacion_cod',
        'nombre': 'nombres_y_apellidos',
        'nombres': 'nombres_y_apellidos',
        'apellidos': 'nombres_y_apellidos_2',
        'nombres_apellidos': 'nombres_y_apellidos',
        'nombres_y_apellidos': 'nombres_y_apellidos',
        'nombre_completo': 'nombres_y_apellidos',
        'nombre_y_apellidos': 'nombres_y_apellidos',
        'instructor': 'nombres_y_apellidos',
        'telefono': 'numero_telefono',
        'celular': 'numero_telefono',
        'numero_de_telefono': 'numero_telefono',
        'telefono_instructor': 'numero_telefono',
        'telefono_contacto': 'numero_telefono',
        'contacto': 'numero_telefono',
        'correo': 'correo_electronico_sena',
        'email': 'correo_electronico_sena',
        'correo_sena': 'correo_electronico_sena',
        'correo_electronico_sena': 'correo_electronico_sena',
        'correo_electronico': 'correo_electronico_sena',
        'correo_personal': 'correo_electronico_personal',
        'correo_electronico_personal': 'correo_electronico_personal',
        'email_personal': 'correo_electronico_personal',
        'fecha_nacimiento': 'fecha_nacimiento',
        'fecha_de_nacimiento': 'fecha_nacimiento',
        'cumpleanos': 'fecha_nacimiento',
        'programas': 'programas_formacion',
        'programas_formacion': 'programas_formacion',
        'programas_de_formacion': 'programas_formacion',
        'programas_a_cargo': 'programas_formacion',
        'programas_de_formacion_a_cargo': 'programas_formacion',
    },
    'fichas': {
        'ficha': 'ficha_7_digitos',
        'ficha_(7_digitos)': 'ficha_7_digitos',
        'numero_ficha': 'ficha_7_digitos',
        'codigo_ficha': 'ficha_7_digitos',
        'ficha_7_digitos': 'ficha_7_digitos',
        'numero': 'ficha_7_digitos',
        'programa': 'programa_nombre',
        'programa_tecnico': 'programa_nombre',
        'programa_nombre': 'programa_nombre',
        'nombre_programa': 'programa_nombre',
        'institucion_educativa': 'institucion_nombre',
        'institucion': 'institucion_nombre',
        'institucion_nombre': 'institucion_nombre',
        'ie': 'institucion_nombre',
        'colegio': 'institucion_nombre',
        'grado': 'grado',
        'municipio': 'municipio',
        'lider': 'lider_nombre',
        'instructor_lider': 'lider_nombre',
        'instructor': 'lider_nombre',
        'lider_nombre': 'lider_nombre',
        'instructor_lider_nombre': 'lider_nombre',
        'cedula_instructor': 'instructor_cedula',
        'id_instructor': 'instructor_cedula',
        'numero_identificacion_instructor': 'instructor_cedula',
        'documento_instructor': 'instructor_cedula',
        'telefono_instructor': 'telefono_instructor',
        'telefono_lider': 'telefono_instructor',
        'correo_instructor': 'correo_instructor',
        'correo_lider': 'correo_instructor',
        'jornada': 'jornada',
        'modalidad': 'modalidad',
        'fecha_inicio': 'fecha_inicio',
        'fecha_fin': 'fecha_fin',
        'programacionrama': 'programa_nombre',
        'programacion': 'programa_nombre',
        'rama': 'programa_nombre',
    },
}


def _cell_value(val):
    if val is None:
        return ''
    if isinstance(val, float) and val.is_integer():
        return str(int(val))
    return str(val).strip()


def _agregar_error(fila, campo, valor, mensaje, recomendacion='', clasificacion=CLASIFICACION_ERROR, lista=None):
    item = {
        'fila': fila,
        'campo': campo,
        'valor': valor,
        'clasificacion': clasificacion,
        'error': mensaje,
        'recomendacion': recomendacion,
    }
    if lista is not None:
        lista.append(item)
    return item


def _parsear_fecha_espanola(texto):
    if not texto:
        return None
    try:
        texto = str(texto).strip().upper()
        m = re.match(r'^(\d{1,2})\s+DE\s+([A-ZÁÉÍÓÚÑ]+)\s+DE\s+(\d{4})$', texto)
        if not m:
            return None
        dia = int(m.group(1))
        mes_nombre = m.group(2)
        anio = int(m.group(3))
        mes = MESES_ES.get(mes_nombre)
        if mes is None:
            return None
        return date(anio, mes, dia)
    except Exception:
        return None


def _split_nombres_apellidos(nombres_y_apellidos):
    if not nombres_y_apellidos:
        return '', ''
    tokens = nombres_y_apellidos.strip().split()
    if len(tokens) <= 2:
        if len(tokens) == 1:
            return tokens[0], ''
        return tokens[0], tokens[1]
    apellidos = tokens[-2:]
    nombres = tokens[:-2]
    if len(nombres) > 2:
        nombres = nombres[:2]
    return ' '.join(nombres), ' '.join(apellidos)


def _generar_codigo_programa(nombre, usados_set=None, existe_bd_fn=None):
    base = re.sub(r'[^A-Z0-9]+', '-', nombre.upper())
    base = base.strip('-')[:20]
    if not base:
        base = 'PROGRAMA'
    candidato = base
    n = 1
    while True:
        usado_archivo = (usados_set is not None) and (candidato in usados_set)
        usado_bd = (existe_bd_fn is not None) and existe_bd_fn(candidato)
        if not usado_archivo and not usado_bd:
            return candidato
        n += 1
        sufijo = f'-{n}'
        candidato = (base[:(20 - len(sufijo))] + sufijo)


class ImportacionExcelService:

    COLUMNAS = {
        'instituciones': [
            'codigo', 'nombre', 'municipio', 'secretaria_educacion', 'telefono',
            'tipo', 'zona', 'sector', 'caracter', 'especialidad', 'direccion',
            'correo_institucional', 'nombre_rector', 'telefono_rector',
            'nombre_coordinador', 'celular_coordinador',
        ],
        'programas': [
            'codigo', 'nombre', 'duracion_meses', 'sector', 'descripcion',
        ],
        'instructores': [
            'tipo_identificacion_cod', 'numero_identificacion',
            'nombres_y_apellidos',
            'numero_telefono',
            'correo_electronico_sena', 'correo_electronico_personal',
            'programas_formacion', 'fecha_nacimiento',
        ],
        'fichas': [
            'ficha_7_digitos', 'programa_nombre', 'institucion_nombre',
            'grado', 'municipio', 'lider_nombre', 'instructor_cedula',
            'telefono_instructor', 'correo_instructor',
            'jornada', 'modalidad', 'fecha_inicio', 'fecha_fin',
        ],
        'proyectos': [
            'codigo', 'nombre', 'descripcion', 'institucion_codigo',
            'programa_codigo', 'instructor_identificacion', 'evento_nombre',
        ],
        'participantes': [
            'tipo_identificacion', 'numero_identificacion', 'nombres', 'apellidos',
            'correo', 'telefono', 'tipo_persona', 'proyecto_codigo',
            'grado', 'entidad', 'cargo',
        ],
    }

    REQUERIDOS = {
        'instituciones': {'nombre', 'municipio'},
        'programas': {'nombre'},
        'instructores': {'numero_identificacion', 'nombres_y_apellidos'},
        'fichas': {'ficha_7_digitos', 'programa_nombre', 'institucion_nombre'},
        'proyectos': {'codigo', 'nombre', 'institucion_codigo', 'programa_codigo', 'evento_nombre'},
        'participantes': {'tipo_identificacion', 'numero_identificacion', 'nombres', 'apellidos', 'tipo_persona'},
    }

    @staticmethod
    def _leer_filas(archivo_excel, start_row=1, header_row=1):
        wb = load_workbook(filename=archivo_excel, read_only=True, data_only=True)
        ws = wb.active
        filas = []
        header = None
        for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if idx == header_row:
                header = [str(c).strip().lower().replace(' ', '_').replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u').rstrip('_') if c is not None else '' for c in row]
                continue
            if idx < start_row:
                continue
            if all((c is None or str(c).strip() == '') for c in row):
                continue
            if header:
                valores = {}
                for i, col in enumerate(header):
                    if col and i < len(row):
                        valores[col] = _cell_value(row[i])
                filas.append((idx, valores))
        wb.close()
        return filas

    @staticmethod
    def validar(archivo_excel, tipo_importacion):
        from apps.eventos.models import Evento, TipoIdentificacion
        from apps.instituciones.models import InstitucionEducativa, Municipio
        from apps.programas.models import ProgramaTecnico
        from apps.personas.models import Persona

        if tipo_importacion not in TIPOS_IMPORTACION:
            raise ValueError(f'Tipo de importación no válido: {tipo_importacion}')

        try:
            filas = ImportacionExcelService._leer_filas(archivo_excel)
        except Exception as e:
            return [{
                'fila': 0,
                'campo': 'archivo',
                'valor': '',
                'clasificacion': CLASIFICACION_ERROR,
                'error': f'No se pudo leer el archivo Excel: {e}',
                'recomendacion': 'Verifique que el archivo sea .xlsx y no esté corrupto.',
                'datos': {},
            }]

        mapeo = MAPEO_HEADERS.get(tipo_importacion, {})
        if mapeo and filas:
            filas_mapeadas = []
            for fila_num, datos in filas:
                nuevos_datos = {}
                for k_old, k_new in mapeo.items():
                    valor = datos.get(k_old)
                    if valor is None:
                        valor = ''
                    valor = str(valor).strip() if not isinstance(valor, str) else valor.strip()
                    if k_new not in nuevos_datos:
                        nuevos_datos[k_new] = valor
                    elif not nuevos_datos[k_new] and valor:
                        nuevos_datos[k_new] = valor
                for k, v in datos.items():
                    if k not in mapeo:
                        v2 = v if isinstance(v, str) else _cell_value(v)
                        if k not in nuevos_datos:
                            nuevos_datos[k] = v2
                        elif not nuevos_datos[k] and v2:
                            nuevos_datos[k] = v2
                filas_mapeadas.append((fila_num, nuevos_datos))
            filas = filas_mapeadas

        resultados = []
        codigos_en_archivo = set()
        ids_en_archivo = set()
        programas_codigos_archivo = set()

        for fila_num, datos in filas:
            fila_resultados = []
            datos_limpios = {}
            clasificacion_fila = CLASIFICACION_VALIDO

            requeridos = ImportacionExcelService.REQUERIDOS.get(tipo_importacion, set())
            for req in requeridos:
                valor = datos.get(req, '')
                if not valor:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR, key=lambda x: CLASIFICACIONES.index(x))
                    _agregar_error(
                        fila_num, req, valor,
                        f'El campo {req} es obligatorio.',
                        f'Diligencie el campo {req} en la fila.',
                        CLASIFICACION_ERROR, fila_resultados,
                    )

            if tipo_importacion == 'instituciones':
                codigo = datos.get('codigo', '')
                nombre = datos.get('nombre', '')
                municipio = datos.get('municipio', '')
                secretaria_educacion = datos.get('secretaria_educacion') or datos.get('secretaria') or ''
                telefono = datos.get('telefono') or datos.get('telefono_ie') or ''
                tipo = datos.get('tipo', '')
                zona = datos.get('zona', '')
                sector = datos.get('sector', '')
                caracter = datos.get('caracter', '')
                especialidad = datos.get('especialidad', '')
                direccion = datos.get('direccion', '')
                correo_institucional = datos.get('correo_institucional') or datos.get('correo') or datos.get('email') or ''
                nombre_rector = datos.get('nombre_rector', '')
                telefono_rector = datos.get('telefono_rector', '')
                nombre_coordinador = datos.get('nombre_coordinador', '')
                celular_coordinador = datos.get('celular_coordinador', '')

                nombre_normalizado = nombre.strip().lower() if nombre else ''
                if codigo:
                    if len(codigo) > 30:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'codigo', codigo, 'Código excede 30 caracteres.', 'Acorte el código a máximo 30 caracteres.', CLASIFICACION_ERROR, fila_resultados)
                    if codigo in codigos_en_archivo:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'codigo', codigo, 'Código repetido en el archivo.', 'Cada institución debe tener un código único.', CLASIFICACION_DUPLICADO, fila_resultados)
                    codigos_en_archivo.add(codigo)
                existe_por_codigo = codigo and InstitucionEducativa.objects.filter(codigo=codigo).exists()
                existe_por_nombre = nombre_normalizado and InstitucionEducativa.objects.filter(nombre__iexact=nombre_normalizado).exists()
                if existe_por_codigo or existe_por_nombre:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                    _agregar_error(fila_num, 'nombre', nombre, 'Institución ya existe en BD (por nombre o código). Se actualizará.', '', CLASIFICACION_DUPLICADO, fila_resultados)
                if nombre and len(nombre) > 250:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'nombre', nombre[:50]+'...', 'Nombre muy largo (máx 250).', 'Se truncará al guardar.', CLASIFICACION_ADVERTENCIA, fila_resultados)
                if correo_institucional and not EMAIL_REGEX.match(correo_institucional):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'correo_institucional', correo_institucional, 'Formato correo no válido.', 'Ej: institucion@dominio.com', CLASIFICACION_ADVERTENCIA, fila_resultados)

                datos_limpios = {
                    'codigo': codigo, 'nombre': nombre, 'municipio': municipio,
                    'secretaria_educacion': secretaria_educacion, 'telefono': telefono,
                    'tipo': tipo, 'zona': zona, 'sector': sector, 'caracter': caracter,
                    'especialidad': especialidad, 'direccion': direccion,
                    'correo_institucional': correo_institucional, 'nombre_rector': nombre_rector,
                    'telefono_rector': telefono_rector, 'nombre_coordinador': nombre_coordinador,
                    'celular_coordinador': celular_coordinador,
                }

            elif tipo_importacion == 'programas':
                nombre = datos.get('nombre', '')
                codigo = datos.get('codigo', '').strip()
                if nombre:
                    if len(nombre) > 200:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                        _agregar_error(fila_num, 'nombre', nombre[:50]+'...', 'Nombre excede 200 caracteres.', '', CLASIFICACION_ADVERTENCIA, fila_resultados)
                    if codigo:
                        if len(codigo) > 30:
                            clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                            _agregar_error(fila_num, 'codigo', codigo, 'Código excede 30 caracteres.', '', CLASIFICACION_ADVERTENCIA, fila_resultados)
                        if codigo in programas_codigos_archivo:
                            clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                            _agregar_error(fila_num, 'codigo', codigo, 'Código repetido en el archivo.', '', CLASIFICACION_DUPLICADO, fila_resultados)
                        programas_codigos_archivo.add(codigo)
                    if ProgramaTecnico.objects.filter(nombre__iexact=nombre).exists():
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'nombre', nombre, 'Programa ya existe en BD. Se actualizará.', '', CLASIFICACION_DUPLICADO, fila_resultados)

                datos_limpios = {'codigo': codigo, 'nombre': nombre}

            elif tipo_importacion == 'instructores':
                nombres_y_apellidos = datos.get('nombres_y_apellidos', '')
                apellidos_solo = datos.get('nombres_y_apellidos_2', '')
                if apellidos_solo and nombres_y_apellidos and not nombres_y_apellidos.endswith(apellidos_solo):
                    nombres_y_apellidos = (nombres_y_apellidos + ' ' + apellidos_solo).strip()

                numero_telefono = datos.get('numero_telefono', '')
                correo_electronico_sena = datos.get('correo_electronico_sena', '')
                correo_electronico_personal = datos.get('correo_electronico_personal', '')
                programas_formacion_str = datos.get('programas_formacion', '')
                fecha_nacimiento_str = datos.get('fecha_nacimiento', '')
                tipo_identificacion_cod = (datos.get('tipo_identificacion_cod') or 'CC').strip().upper() or 'CC'

                # Traducción común TIPO_ID: nombres completos a códigos
                if tipo_identificacion_cod in ('CÉDULA DE CIUDADANÍA', 'CEDULA DE CIUDADANIA', 'CC.', 'C.C', 'CC', 'CEDULA'):
                    tipo_identificacion_cod = 'CC'
                elif tipo_identificacion_cod in ('TARJETA DE IDENTIDAD', 'TI.', 'T.I', 'TI', 'TARJETA IDENTIDAD'):
                    tipo_identificacion_cod = 'TI'
                elif tipo_identificacion_cod in ('PERMISO POR PROTECCIÓN TEMPORAL', 'PPT', 'PERMISO TEMPORAL'):
                    tipo_identificacion_cod = 'PPT'

                nombres, apellidos = _split_nombres_apellidos(nombres_y_apellidos)

                tipo_identificacion_id = None
                try:
                    tipo_id_obj = TipoIdentificacion.objects.get(codigo__iexact=tipo_identificacion_cod, activo=True)
                    tipo_identificacion_id = tipo_id_obj.id
                except TipoIdentificacion.DoesNotExist:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                    _agregar_error(
                        fila_num, 'tipo_identificacion_cod', tipo_identificacion_cod,
                        f'Tipo de identificación "{tipo_identificacion_cod}" no existe. Use CC, TI o PPT.',
                        'Verifique el tipo de identificación (CC, TI, PPT).',
                        CLASIFICACION_ERROR, fila_resultados,
                    )

                numero_identificacion = (datos.get('numero_identificacion') or '').strip()
                if not numero_identificacion:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                    _agregar_error(
                        fila_num, 'numero_identificacion', '',
                        'El número de identificación (cédula) es obligatorio.',
                        'Diligencie la cédula del instructor.',
                        CLASIFICACION_ERROR, fila_resultados,
                    )
                if numero_identificacion and len(numero_identificacion) < 5:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(
                        fila_num, 'numero_identificacion', numero_identificacion,
                        'Número de identificación muy corto (mínimo 5 dígitos).',
                        'Verifique el número de cédula.',
                        CLASIFICACION_ADVERTENCIA, fila_resultados,
                    )

                clave_unica = (tipo_identificacion_cod, numero_identificacion)
                if numero_identificacion:
                    if clave_unica in ids_en_archivo:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'numero_identificacion', numero_identificacion,
                                       'Instructor repetido en archivo (mismo ID).',
                                       '', CLASIFICACION_DUPLICADO, fila_resultados)
                    ids_en_archivo.add(clave_unica)
                    if tipo_identificacion_id and Persona.objects.filter(
                        tipo_identificacion_id=tipo_identificacion_id,
                        numero_identificacion=numero_identificacion,
                    ).exists():
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'nombres_y_apellidos', nombres_y_apellidos,
                                       'Instructor ya existe en BD (mismo ID). Se actualizará.',
                                       '', CLASIFICACION_DUPLICADO, fila_resultados)

                if correo_electronico_sena and not EMAIL_REGEX.match(correo_electronico_sena):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'correo_electronico_sena', correo_electronico_sena, 'Formato correo SENA no válido.', 'Ej: instructor@sena.edu.co', CLASIFICACION_ADVERTENCIA, fila_resultados)
                if correo_electronico_personal and not EMAIL_REGEX.match(correo_electronico_personal):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'correo_electronico_personal', correo_electronico_personal, 'Formato correo personal no válido.', 'Ej: instructor@gmail.com', CLASIFICACION_ADVERTENCIA, fila_resultados)

                fecha_nacimiento = None
                if fecha_nacimiento_str:
                    if isinstance(fecha_nacimiento_str, (date, datetime)):
                        fecha_nacimiento = fecha_nacimiento_str if isinstance(fecha_nacimiento_str, date) else fecha_nacimiento_str.date()
                    else:
                        fecha_nacimiento = _parsear_fecha_espanola(fecha_nacimiento_str)
                    if fecha_nacimiento is None:
                        try:
                            import datetime as _dt
                            if re.match(r'^\d{4}-\d{2}-\d{2}$', str(fecha_nacimiento_str)):
                                y, m, d = str(fecha_nacimiento_str).split('-')
                                fecha_nacimiento = _dt.date(int(y), int(m), int(d))
                        except Exception:
                            pass
                    if fecha_nacimiento is None:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                        _agregar_error(
                            fila_num, 'fecha_nacimiento', fecha_nacimiento_str,
                            'Formato fecha no reconocido. Use "YYYY-MM-DD", "17 DE AGOSTO DE 1981" o fecha Excel.',
                            '', CLASIFICACION_ADVERTENCIA, fila_resultados,
                        )

                programas_nombres = []
                programas_nombres_existentes = []
                if programas_formacion_str:
                    partes = re.split(r'[,;|/]+', programas_formacion_str)
                    for p in partes:
                        p = p.strip()
                        if p:
                            programas_nombres.append(p)
                            prog = ProgramaTecnico.objects.filter(nombre__iexact=p, activo=True).first()
                            if prog:
                                programas_nombres_existentes.append(p)
                            else:
                                clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                                _agregar_error(
                                    fila_num, 'programas_formacion', p,
                                    f'Programa "{p}" no existe. Se omitirá la asociación.',
                                    'Primero importe los programas.',
                                    CLASIFICACION_ADVERTENCIA, fila_resultados,
                                )

                datos_limpios = {
                    'tipo_identificacion_cod': tipo_identificacion_cod,
                    'tipo_identificacion_id': tipo_identificacion_id,
                    'numero_identificacion': numero_identificacion,
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'correo_sena': correo_electronico_sena or None,
                    'correo_personal': correo_electronico_personal or None,
                    'telefono': numero_telefono or None,
                    'fecha_nacimiento': fecha_nacimiento.isoformat() if fecha_nacimiento else None,
                    'programas_nombres': programas_nombres_existentes,
                }

            elif tipo_importacion == 'fichas':
                ficha_7_digitos = datos.get('ficha_7_digitos', '')
                programa_nombre = datos.get('programa_nombre', '')
                institucion_nombre = datos.get('institucion_nombre', '')
                grado = datos.get('grado', '')
                municipio = datos.get('municipio', '')
                lider_nombre = datos.get('lider_nombre', '')
                instructor_cedula = datos.get('instructor_cedula', '') or ''
                telefono_instructor = datos.get('telefono_instructor', '')
                correo_instructor = datos.get('correo_instructor', '')
                jornada = datos.get('jornada', '') or None
                modalidad = datos.get('modalidad', '') or None
                fecha_inicio = datos.get('fecha_inicio', '') or None
                fecha_fin = datos.get('fecha_fin', '') or None

                if ficha_7_digitos:
                    ficha_solo_numeros = re.sub(r'\D', '', ficha_7_digitos)
                    if not FICHA_NUMERO_REGEX.match(ficha_solo_numeros):
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(
                            fila_num, 'ficha_7_digitos', ficha_7_digitos,
                            'Número de ficha debe tener exactamente 7 dígitos numéricos.',
                            'Verifique que el número de ficha contenga 7 dígitos.',
                            CLASIFICACION_ERROR, fila_resultados,
                        )
                    else:
                        ficha_7_digitos = ficha_solo_numeros

                    if ficha_7_digitos in codigos_en_archivo:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'ficha_7_digitos', ficha_7_digitos, 'Ficha repetida en el archivo.', 'Cada ficha debe ser única.', CLASIFICACION_DUPLICADO, fila_resultados)
                    codigos_en_archivo.add(ficha_7_digitos)
                    from apps.proyectos.models import Ficha
                    if Ficha.objects.filter(numero=ficha_7_digitos).exists():
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'ficha_7_digitos', ficha_7_digitos, 'Ficha ya existe en BD. Se actualizará.', '', CLASIFICACION_DUPLICADO, fila_resultados)

                institucion_id = None
                if institucion_nombre:
                    inst = InstitucionEducativa.objects.filter(nombre__iexact=institucion_nombre, activo=True).first()
                    if inst:
                        institucion_id = inst.id
                    else:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(
                            fila_num, 'institucion_nombre', institucion_nombre,
                            'Institución no existe o inactiva.',
                            'Importe primero las instituciones o verifique el nombre.',
                            CLASIFICACION_ERROR, fila_resultados,
                        )

                programa_id = None
                if programa_nombre:
                    prog = ProgramaTecnico.objects.filter(nombre__iexact=programa_nombre, activo=True).first()
                    if prog:
                        programa_id = prog.id
                    else:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(
                            fila_num, 'programa_nombre', programa_nombre,
                            'Programa no existe o inactivo.',
                            'Importe primero los programas o verifique el nombre.',
                            CLASIFICACION_ERROR, fila_resultados,
                        )

                instructor_lider_id = None
                if instructor_cedula or lider_nombre or correo_instructor:
                    from apps.personas.models import Persona as PersonaModel
                    from apps.instructores.models import Instructor
                    qs = Instructor.objects.filter(activo=True).select_related('persona')
                    encontrado = None
                    if instructor_cedula:
                        encontrado = qs.filter(persona__numero_identificacion=str(instructor_cedula).strip()).first()
                    if not encontrado and correo_instructor:
                        encontrado = qs.filter(
                            models.Q(persona__correo_sena__iexact=correo_instructor)
                            | models.Q(persona__correo_personal__iexact=correo_instructor)
                            | models.Q(persona__correo__iexact=correo_instructor)
                        ).first()
                    if not encontrado and lider_nombre:
                        tokens = lider_nombre.strip().split()
                        if len(tokens) >= 2:
                            encontrado = qs.filter(
                                persona__nombres__icontains=tokens[0],
                                persona__apellidos__icontains=tokens[-1],
                            ).first()
                        else:
                            encontrado = qs.filter(
                                models.Q(persona__nombres__icontains=lider_nombre)
                                | models.Q(persona__apellidos__icontains=lider_nombre)
                            ).first()
                    if encontrado:
                        instructor_lider_id = encontrado.id
                    elif lider_nombre or correo_instructor or instructor_cedula:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                        _agregar_error(
                            fila_num, 'instructor_lider', lider_nombre or instructor_cedula,
                            'Instructor líder no encontrado. Se guardará la ficha sin instructor asignado.',
                            'Verifique el nombre/cédula/correo del instructor (instructores deben importarse primero).',
                            CLASIFICACION_ADVERTENCIA, fila_resultados,
                        )

                if correo_instructor and not EMAIL_REGEX.match(correo_instructor):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'correo_instructor', correo_instructor, 'Formato correo instructor no válido.', '', CLASIFICACION_ADVERTENCIA, fila_resultados)

                datos_limpios = {
                    'numero': ficha_7_digitos,
                    'programa_nombre': programa_nombre,
                    'institucion_nombre': institucion_nombre,
                    'institucion_id': institucion_id,
                    'programa_id': programa_id,
                    'grado': grado,
                    'municipio': municipio,
                    'instructor_lider_id': instructor_lider_id,
                    'instructor_cedula': instructor_cedula,
                    'telefono_instructor': telefono_instructor,
                    'correo_instructor': correo_instructor,
                    'jornada': jornada,
                    'modalidad': modalidad,
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                }

            elif tipo_importacion == 'proyectos':
                codigo = datos.get('codigo', '')
                nombre = datos.get('nombre', '')
                descripcion = datos.get('descripcion', '')
                inst_cod = datos.get('institucion_codigo', '')
                prog_cod = datos.get('programa_codigo', '')
                instr_id = datos.get('instructor_identificacion', '')
                evento_nombre = datos.get('evento_nombre', '')

                institucion = None
                if inst_cod:
                    try:
                        institucion = InstitucionEducativa.objects.get(codigo=inst_cod, activo=True)
                    except InstitucionEducativa.DoesNotExist:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'institucion_codigo', inst_cod, 'Institución no existe o inactiva.', 'Importe primero las instituciones.', CLASIFICACION_ERROR, fila_resultados)

                programa = None
                if prog_cod:
                    try:
                        programa = ProgramaTecnico.objects.get(codigo=prog_cod, activo=True)
                    except ProgramaTecnico.DoesNotExist:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'programa_codigo', prog_cod, 'Programa no existe o inactivo.', 'Importe primero los programas.', CLASIFICACION_ERROR, fila_resultados)

                evento = None
                if evento_nombre:
                    try:
                        evento = Evento.objects.filter(nombre__icontains=evento_nombre, activo=True).first()
                        if not evento:
                            evento = Evento.objects.filter(nombre=evento_nombre).first()
                        if not evento:
                            raise Evento.DoesNotExist
                    except Evento.DoesNotExist:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'evento_nombre', evento_nombre, 'Evento no encontrado.', 'Verifique el nombre del evento en el sistema.', CLASIFICACION_ERROR, fila_resultados)

                instructor = None
                if instr_id:
                    from apps.instructores.models import Instructor
                    instr_persona = Persona.objects.filter(
                        numero_identificacion=instr_id, tipo_persona='INSTRUCTOR'
                    ).first()
                    if not instr_persona:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                        _agregar_error(fila_num, 'instructor_identificacion', instr_id, 'Instructor no encontrado.', 'Se guardará el proyecto sin instructor responsable.', CLASIFICACION_ADVERTENCIA, fila_resultados)
                    else:
                        try:
                            instructor = Instructor.objects.get(persona=instr_persona)
                        except Instructor.DoesNotExist:
                            pass

                if codigo and evento:
                    if (evento.id, codigo) in codigos_en_archivo:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'codigo', codigo, 'Código repetido para este evento en el archivo.', '', CLASIFICACION_DUPLICADO, fila_resultados)
                    codigos_en_archivo.add((evento.id, codigo))
                    from apps.proyectos.models import Proyecto
                    if Proyecto.objects.filter(evento=evento, codigo=codigo).exists():
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'codigo', codigo, 'Proyecto ya existe en este evento. Se actualizará.', '', CLASIFICACION_DUPLICADO, fila_resultados)

                datos_limpios = {
                    'codigo': codigo,
                    'nombre': nombre,
                    'descripcion': descripcion,
                    'institucion_id': institucion.id if institucion else None,
                    'programa_id': programa.id if programa else None,
                    'instructor_id': instructor.id if instructor else None,
                    'evento_id': evento.id if evento else None,
                }

            elif tipo_importacion == 'participantes':
                tipo_id_cod = (datos.get('tipo_identificacion', '') or '').strip().upper() or ''
                numero_id = datos.get('numero_identificacion', '')
                nombres = datos.get('nombres', '')
                apellidos = datos.get('apellidos', '')
                correo = datos.get('correo', '')
                telefono = datos.get('telefono', '')
                tipo_persona_raw = datos.get('tipo_persona', '') or ''
                tipo_persona = str(tipo_persona_raw).strip().upper()
                proyecto_codigo = datos.get('proyecto_codigo', '')
                grado = datos.get('grado', '11')
                entidad = datos.get('entidad', '')
                cargo = datos.get('cargo', '')

                # =================================================================
                # ✅ Mapeo MUY FÁCIL TIPO_PERSONA: acepta abreviaturas /
                # variaciones para que el usuario no tenga que escribir
                # exactamente "APRENDIZ / INSTRUCTOR / INVITADO / ORGANIZADOR".
                #
                # O | ORG | ORGANIZ | ORGANIZADO  ->  ORGANIZADOR
                # I | INS | INSTRUCTOR            ->  INSTRUCTOR
                # A | APR | APRENDIZ              ->  APRENDIZ
                # V | INV | INVI | INVITADO       ->  INVITADO
                # =================================================================
                _TIPO_ALIAS = {
                    'O': 'ORGANIZADOR', 'ORG': 'ORGANIZADOR',
                    'ORGANIZ': 'ORGANIZADOR', 'ORGANIZADO': 'ORGANIZADOR',
                    'ORGANIZADORES': 'ORGANIZADOR', 'ORGANIZADOR': 'ORGANIZADOR',
                    'I': 'INSTRUCTOR', 'INS': 'INSTRUCTOR',
                    'INST': 'INSTRUCTOR', 'INSTRUCTOR': 'INSTRUCTOR',
                    'INSTRUCTORES': 'INSTRUCTOR',
                    'A': 'APRENDIZ', 'APR': 'APRENDIZ',
                    'APREND': 'APRENDIZ', 'APRENDIZ': 'APRENDIZ',
                    'APRENDICES': 'APRENDIZ',
                    'V': 'INVITADO', 'IV': 'INVITADO',
                    'INV': 'INVITADO', 'INVI': 'INVITADO',
                    'INVIT': 'INVITADO', 'INVITADO': 'INVITADO',
                    'INVITADOS': 'INVITADO',
                }
                if tipo_persona and tipo_persona in _TIPO_ALIAS:
                    tipo_persona = _TIPO_ALIAS[tipo_persona]

                if tipo_persona and tipo_persona not in dict(Persona.TIPOS):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                    _agregar_error(fila_num, 'tipo_persona', tipo_persona, 'Tipo de persona no válido.', 'Valores permitidos: APRENDIZ, INSTRUCTOR, INVITADO, ORGANIZADOR.', CLASIFICACION_ERROR, fila_resultados)

                # Traducción común TIPO_ID: nombres completos a códigos (mismo flujo instructores)
                if tipo_id_cod in ('CÉDULA DE CIUDADANÍA', 'CEDULA DE CIUDADANIA', 'CC.', 'C.C', 'CC', 'CEDULA'):
                    tipo_id_cod = 'CC'
                elif tipo_id_cod in ('TARJETA DE IDENTIDAD', 'TI.', 'T.I', 'TI', 'TARJETA IDENTIDAD'):
                    tipo_id_cod = 'TI'
                elif tipo_id_cod in ('PERMISO POR PROTECCIÓN TEMPORAL', 'PPT', 'PERMISO TEMPORAL'):
                    tipo_id_cod = 'PPT'
                elif tipo_id_cod in ('CÉDULA DE EXTRANJERÍA', 'CEDULA DE EXTRANJERIA', 'CE.', 'C.E', 'CE'):
                    tipo_id_cod = 'CE'
                elif tipo_id_cod in ('PASAPORTE', 'PAS', 'PA', 'P'):
                    tipo_id_cod = 'PASAPORTE'

                tipo_id_obj = None
                if tipo_id_cod:
                    try:
                        tipo_id_obj = TipoIdentificacion.objects.get(codigo__iexact=tipo_id_cod, activo=True)
                    except TipoIdentificacion.DoesNotExist:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'tipo_identificacion', tipo_id_cod, 'Tipo identificación no existe. Valores permitidos: CC, TI, PPT, CE, PASAPORTE.', '', CLASIFICACION_ERROR, fila_resultados)

                clave_unica = (tipo_id_cod, numero_id)
                if numero_id:
                    if clave_unica in ids_en_archivo:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'numero_identificacion', numero_id, 'Persona repetida en archivo.', '', CLASIFICACION_DUPLICADO, fila_resultados)
                    ids_en_archivo.add(clave_unica)
                    if tipo_id_obj and Persona.objects.filter(tipo_identificacion=tipo_id_obj, numero_identificacion=numero_id).exists():
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_DUPLICADO)
                        _agregar_error(fila_num, 'numero_identificacion', numero_id, 'Persona ya existe en BD. Se actualizará.', '', CLASIFICACION_DUPLICADO, fila_resultados)

                if correo and not EMAIL_REGEX.match(correo):
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'correo', correo, 'Formato correo no válido.', '', CLASIFICACION_ADVERTENCIA, fila_resultados)

                proyecto = None
                if tipo_persona == 'APRENDIZ' and proyecto_codigo:
                    from apps.proyectos.models import Proyecto
                    proyecto = Proyecto.objects.filter(codigo=proyecto_codigo).first()
                    if not proyecto:
                        clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                        _agregar_error(fila_num, 'proyecto_codigo', proyecto_codigo, 'Proyecto no existe.', 'Importe primero los proyectos.', CLASIFICACION_ERROR, fila_resultados)

                if tipo_persona == 'APRENDIZ' and not proyecto_codigo:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ERROR)
                    _agregar_error(fila_num, 'proyecto_codigo', '', 'Aprendiz requiere proyecto_codigo.', '', CLASIFICACION_ERROR, fila_resultados)
                if tipo_persona == 'INVITADO' and not entidad:
                    clasificacion_fila = max(clasificacion_fila, CLASIFICACION_ADVERTENCIA)
                    _agregar_error(fila_num, 'entidad', entidad, 'Invitado debería tener entidad.', '', CLASIFICACION_ADVERTENCIA, fila_resultados)

                datos_limpios = {
                    'tipo_identificacion_id': tipo_id_obj.id if tipo_id_obj else None,
                    'numero_identificacion': numero_id,
                    'nombres': nombres,
                    'apellidos': apellidos,
                    'correo': correo,
                    'telefono': telefono,
                    'tipo_persona': tipo_persona,
                    'proyecto_id': proyecto.id if proyecto else None,
                    'grado': grado,
                    'entidad': entidad,
                    'cargo': cargo,
                }

            for r in fila_resultados:
                resultados.append({**r, 'datos': datos_limpios})
            if not fila_resultados or clasificacion_fila in (CLASIFICACION_VALIDO, CLASIFICACION_ADVERTENCIA, CLASIFICACION_DUPLICADO):
                resultados.append({
                    'fila': fila_num,
                    'campo': '__fila__',
                    'valor': '',
                    'clasificacion': clasificacion_fila,
                    'error': '',
                    'recomendacion': '',
                    'datos': datos_limpios,
                })

        return resultados

    @staticmethod
    def estadisticas(resultados):
        stats = {c: 0 for c in CLASIFICACIONES}
        filas_procesadas = set()
        for r in resultados:
            if r.get('campo') == '__fila__':
                stats[r['clasificacion']] += 1
                filas_procesadas.add(r['fila'])
        stats['TOTAL'] = sum(stats[c] for c in CLASIFICACIONES)
        return stats

    @staticmethod
    def preview(request, resultados_validados):
        return {
            'resultados': resultados_validados,
            'estadisticas': ImportacionExcelService.estadisticas(resultados_validados),
        }

    @staticmethod
    def _serializar_para_confirmar(resultados):
        import json
        import zlib
        import base64
        datos = [
            r for r in resultados
            if r.get('campo') == '__fila__'
            and r.get('clasificacion') in (CLASIFICACION_VALIDO, CLASIFICACION_ADVERTENCIA, CLASIFICACION_DUPLICADO)
        ]
        json_str = json.dumps(datos, ensure_ascii=False, default=str)
        comprimido = zlib.compress(json_str.encode('utf-8'), 9)
        return base64.urlsafe_b64encode(comprimido).decode('utf-8')

    @staticmethod
    @transaction.atomic
    def confirmar(request, tipo, resultados_solo_validos):
        from apps.auditoria.models import AuditLog
        from apps.eventos.models import TipoIdentificacion
        from apps.instituciones.models import InstitucionEducativa, Municipio
        from apps.programas.models import ProgramaTecnico
        from apps.personas.models import Persona
        from apps.instructores.models import Instructor
        from apps.proyectos.models import Proyecto, Aprendiz as ProyectoAprendiz, Ficha
        from apps.invitados.models import Invitado

        creados = 0
        actualizados = 0
        total = 0

        filas_datos = [
            r for r in resultados_solo_validos
            if r.get('campo') == '__fila__'
            and r.get('clasificacion') in (CLASIFICACION_VALIDO, CLASIFICACION_ADVERTENCIA, CLASIFICACION_DUPLICADO)
        ]

        datos_resumen = {
            'tipo_importacion': tipo,
            'filas_procesadas': len(filas_datos),
            'detalle': [],
        }

        for r in filas_datos:
            datos = r.get('datos') or {}
            total += 1
            info_fila = {'fila': r['fila'], 'accion': None, 'id': None}

            if tipo == 'instituciones':
                if not datos.get('nombre'):
                    continue
                # Resolver FK Municipio: get_or_create por nombre UPPER; default departamento LA GUAJIRA
                mun_nombre = ''
                mun_departamento_default = 'LA GUAJIRA'
                if datos.get('municipio'):
                    mun_nombre = str(datos['municipio']).strip().upper()[:100]
                elif datos.get('municipio_nombre'):
                    mun_nombre = str(datos['municipio_nombre']).strip().upper()[:100]
                if datos.get('departamento'):
                    mun_departamento_default = str(datos['departamento']).strip().upper()[:100] or mun_departamento_default
                if datos.get('departamento_ie'):
                    mun_departamento_default = str(datos['departamento_ie']).strip().upper()[:100] or mun_departamento_default
                municipio_obj = None
                if mun_nombre:
                    municipio_obj, _mun_created = Municipio.objects.get_or_create(
                        nombre=mun_nombre,
                        defaults={'departamento': mun_departamento_default}
                    )
                    if _mun_created:
                        # si no lo creamos con defaults (existe pero sin departamento), actualizar dept si está vacío
                        pass
                    else:
                        # Actualizar departamento si no tenía
                        if not municipio_obj.departamento and mun_departamento_default:
                            municipio_obj.departamento = mun_departamento_default
                            municipio_obj.save(update_fields=['departamento'])
                defaults = {
                    'nombre': datos['nombre'][:250],
                    'secretaria_educacion': (datos.get('secretaria_educacion') or datos.get('secretaria') or '')[:150],
                    'telefono': (datos.get('telefono') or datos.get('telefono_ie') or '')[:30] or None,
                    'tipo': (datos.get('tipo') or '')[:50] or None,
                    'zona': (datos.get('zona') or '')[:30] or None,
                    'sector': (datos.get('sector') or '')[:30] or None,
                    'caracter': (datos.get('caracter') or '')[:50] or None,
                    'especialidad': (datos.get('especialidad') or '')[:150] or None,
                    'direccion': (datos.get('direccion') or '')[:250] or None,
                    'correo_institucional': datos.get('correo_institucional') or None,
                    'nombre_rector': (datos.get('nombre_rector') or '')[:180] or None,
                    'telefono_rector': (datos.get('telefono_rector') or '')[:30] or None,
                    'nombre_coordinador': (datos.get('nombre_coordinador') or '')[:180] or None,
                    'celular_coordinador': (datos.get('celular_coordinador') or '')[:30] or None,
                    'activo': True,
                }
                if municipio_obj is not None:
                    defaults['municipio'] = municipio_obj
                obj = InstitucionEducativa.objects.filter(nombre__iexact=datos['nombre']).first()
                created = False
                if obj is None:
                    if datos.get('codigo') or datos.get('codigo_dane'):
                        cod = (datos.get('codigo') or datos.get('codigo_dane')).strip().upper()
                        obj = InstitucionEducativa.objects.filter(codigo=cod).first()
                    if obj is None:
                        if datos.get('codigo') or datos.get('codigo_dane'):
                            defaults['codigo'] = (datos.get('codigo') or datos.get('codigo_dane')).strip().upper()
                        obj = InstitucionEducativa.objects.create(**defaults)
                        created = True
                    else:
                        for k, v in defaults.items():
                            setattr(obj, k, v)
                        if datos.get('codigo') or datos.get('codigo_dane'):
                            obj.codigo = (datos.get('codigo') or datos.get('codigo_dane')).strip().upper()
                        obj.save()
                else:
                    for k, v in defaults.items():
                        setattr(obj, k, v)
                    if not obj.codigo and (datos.get('codigo') or datos.get('codigo_dane')):
                        obj.codigo = (datos.get('codigo') or datos.get('codigo_dane')).strip().upper()
                    obj.save()
                info_fila['accion'] = 'CREATE' if created else 'UPDATE'
                info_fila['id'] = obj.id
                if created:
                    creados += 1
                else:
                    actualizados += 1

            elif tipo == 'programas':
                if not datos.get('nombre'):
                    continue
                nombre = datos['nombre']
                codigo = (datos.get('codigo') or '').strip().upper() or None
                obj = ProgramaTecnico.objects.filter(nombre__iexact=nombre).first()
                created = False
                if obj is None and codigo:
                    obj = ProgramaTecnico.objects.filter(codigo=codigo).first()
                if obj is None:
                    create_kwargs = {
                        'nombre': nombre[:200],
                        'activo': True,
                    }
                    if codigo:
                        create_kwargs['codigo'] = codigo
                    obj = ProgramaTecnico.objects.create(**create_kwargs)
                    created = True
                else:
                    obj.nombre = nombre[:200]
                    obj.activo = True
                    if codigo and not obj.codigo:
                        obj.codigo = codigo
                    obj.save()
                info_fila['accion'] = 'CREATE' if created else 'UPDATE'
                info_fila['id'] = obj.id
                if created:
                    creados += 1
                else:
                    actualizados += 1

            elif tipo == 'instructores':
                if not datos.get('tipo_identificacion_id') or not datos.get('numero_identificacion'):
                    continue
                persona_defaults = {
                    'nombres': (datos.get('nombres') or '')[:120],
                    'apellidos': (datos.get('apellidos') or '')[:120],
                    'telefono': datos.get('telefono') or None,
                    'correo_sena': datos.get('correo_sena') or None,
                    'correo_personal': datos.get('correo_personal') or None,
                    'fecha_nacimiento': datos.get('fecha_nacimiento') or None,
                    'tipo_persona': 'INSTRUCTOR',
                    'activo': True,
                }
                if request and hasattr(request, 'user') and request.user.is_authenticated:
                    persona_defaults['creado_por'] = request.user
                persona, p_created = Persona.objects.update_or_create(
                    tipo_identificacion_id=datos['tipo_identificacion_id'],
                    numero_identificacion=datos['numero_identificacion'],
                    defaults=persona_defaults,
                )
                # Asegurarse perfil instructor activo
                instructor, i_created = Instructor.objects.get_or_create(persona=persona)
                if not i_created and not instructor.activo:
                    instructor.activo = True
                    instructor.save(update_fields=['activo'])
                programas_nombres = datos.get('programas_nombres') or []
                if programas_nombres:
                    progs = ProgramaTecnico.objects.filter(nombre__in=[p for p in programas_nombres])
                    if progs.exists():
                        instructor.programas.set(list(progs))
                info_fila['accion'] = 'CREATE' if p_created else 'UPDATE'
                info_fila['id'] = persona.id
                if p_created:
                    creados += 1
                else:
                    actualizados += 1

            elif tipo == 'fichas':
                if not datos.get('numero') or not datos.get('institucion_id') or not datos.get('programa_id'):
                    continue
                defaults = {}
                if datos.get('grado') is not None:
                    defaults['grado'] = str(datos.get('grado') or '11')[:10] or '11'
                if datos.get('municipio') is not None:
                    defaults['municipio'] = (datos.get('municipio') or '')[:100] or None
                if datos.get('instructor_lider_id'):
                    defaults['instructor_lider_id'] = datos['instructor_lider_id']
                if datos.get('telefono_instructor'):
                    defaults['telefono_instructor'] = (str(datos.get('telefono_instructor') or '')[:30] or None)
                if datos.get('correo_instructor'):
                    defaults['correo_instructor'] = (datos.get('correo_instructor') or None)
                for campof, campod in [('fecha_inicio', 'fecha_inicio'), ('fecha_fin', 'fecha_fin')]:
                    v = datos.get(campof)
                    if v:
                        if isinstance(v, (date, datetime)):
                            defaults[campod] = v if isinstance(v, date) else v.date()
                        else:
                            vs = str(v).strip()
                            m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', vs)
                            if m:
                                try:
                                    defaults[campod] = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                                except Exception:
                                    pass
                defaults['institucion_id'] = datos['institucion_id']
                defaults['programa_id'] = datos['programa_id']
                defaults['activo'] = True
                obj, created = Ficha.objects.update_or_create(
                    numero=datos['numero'],
                    defaults=defaults,
                )
                info_fila['accion'] = 'CREATE' if created else 'UPDATE'
                info_fila['id'] = obj.id
                if created:
                    creados += 1
                else:
                    actualizados += 1

            elif tipo == 'proyectos':
                if not datos.get('codigo') or not datos.get('evento_id'):
                    continue
                defaults = {
                    'nombre': (datos.get('nombre') or '')[:250],
                    'descripcion': datos.get('descripcion') or '',
                }
                if datos.get('institucion_id'):
                    defaults['institucion_id'] = datos['institucion_id']
                if datos.get('programa_id'):
                    defaults['programa_id'] = datos['programa_id']
                if datos.get('instructor_id'):
                    defaults['instructor_responsable_id'] = datos['instructor_id']
                obj, created = Proyecto.objects.update_or_create(
                    evento_id=datos['evento_id'],
                    codigo=datos['codigo'],
                    defaults=defaults,
                )
                info_fila['accion'] = 'CREATE' if created else 'UPDATE'
                info_fila['id'] = obj.id
                if created:
                    creados += 1
                else:
                    actualizados += 1

            elif tipo == 'participantes':
                if not datos.get('tipo_identificacion_id') or not datos.get('numero_identificacion') or not datos.get('tipo_persona'):
                    continue
                persona_defaults = {
                    'nombres': (datos.get('nombres') or '')[:120],
                    'apellidos': (datos.get('apellidos') or '')[:120],
                    'correo': datos.get('correo') or None,
                    'telefono': datos.get('telefono') or None,
                    'tipo_persona': datos['tipo_persona'],
                }
                if request and hasattr(request, 'user') and request.user.is_authenticated:
                    persona_defaults['creado_por'] = request.user
                persona, p_created = Persona.objects.update_or_create(
                    tipo_identificacion_id=datos['tipo_identificacion_id'],
                    numero_identificacion=datos['numero_identificacion'],
                    defaults=persona_defaults,
                )
                info_fila['id'] = persona.id

                if datos['tipo_persona'] == 'APRENDIZ' and datos.get('proyecto_id'):
                    ProyectoAprendiz.objects.update_or_create(
                        persona=persona,
                        defaults={
                            'proyecto_id': datos['proyecto_id'],
                            'grado': datos.get('grado') or '11',
                        },
                    )
                elif datos['tipo_persona'] == 'INVITADO':
                    Invitado.objects.update_or_create(
                        persona=persona,
                        defaults={
                            'entidad': (datos.get('entidad') or '')[:200],
                            'cargo': (datos.get('cargo') or '')[:150],
                        },
                    )
                elif datos['tipo_persona'] == 'INSTRUCTOR':
                    Instructor.objects.get_or_create(persona=persona)
                elif datos['tipo_persona'] == 'ORGANIZADOR':
                    from apps.organizadores.models import Organizador
                    Organizador.objects.get_or_create(persona=persona, defaults={
                        'cargo': (datos.get('cargo') or '')[:150] or None,
                        'area_responsabilidad': (datos.get('entidad') or '')[:200] or None,
                    })

                info_fila['accion'] = 'CREATE' if p_created else 'UPDATE'
                if p_created:
                    creados += 1
                else:
                    actualizados += 1

            datos_resumen['detalle'].append(info_fila)

        datos_resumen['creados'] = creados
        datos_resumen['actualizados'] = actualizados

        ip = None
        ua = ''
        if request:
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            ua = request.META.get('HTTP_USER_AGENT', '')[:255]
        usuario = getattr(request, 'user', None) if request else None
        if not (usuario and usuario.is_authenticated):
            usuario = None

        AuditLog.objects.create(
            usuario=usuario,
            accion='IMPORT',
            modulo='REPORTES',
            entidad=f'importacion_{tipo}',
            id_entidad=None,
            datos=datos_resumen,
            ip=ip,
            user_agent=ua,
        )

        return datos_resumen

    @staticmethod
    def generar_reporte_errores_xlsx(resultados_con_errores):
        wb = Workbook()
        ws = wb.active
        ws.title = 'Errores Importación'

        encabezados = ['FILA', 'CAMPO', 'VALOR', 'CLASIFICACION', 'ERROR', 'RECOMENDACION']
        ws.append(encabezados)

        font_bold = Font(bold=True, color='FFFFFF')
        fill_header = PatternFill(start_color='39A900', end_color='39A900', fill_type='solid')
        fill_error = PatternFill(start_color='FDECEA', end_color='FDECEA', fill_type='solid')
        fill_dup = PatternFill(start_color='FFF3CD', end_color='FFF3CD', fill_type='solid')
        fill_warn = PatternFill(start_color='FFF8E1', end_color='FFF8E1', fill_type='solid')
        fill_ok = PatternFill(start_color='E8F5E9', end_color='E8F5E9', fill_type='solid')

        for cell in ws[1]:
            cell.font = font_bold
            cell.fill = fill_header
            cell.alignment = Alignment(horizontal='center', vertical='center')

        filas_reales = [
            r for r in resultados_con_errores
            if r.get('campo') != '__fila__'
            or r.get('clasificacion') in (CLASIFICACION_ERROR,)
        ]
        if not filas_reales:
            filas_reales = resultados_con_errores

        for r in filas_reales:
            valor = (r.get('valor') or '')
            if len(valor) > 200:
                valor = valor[:197] + '...'
            ws.append([
                r.get('fila', ''),
                r.get('campo', ''),
                valor,
                r.get('clasificacion', ''),
                (r.get('error') or '')[:500],
                (r.get('recomendacion') or '')[:500],
            ])
            row_idx = ws.max_row
            clasif = r.get('clasificacion', '')
            fill = None
            if clasif == CLASIFICACION_ERROR:
                fill = fill_error
            elif clasif == CLASIFICACION_DUPLICADO:
                fill = fill_dup
            elif clasif == CLASIFICACION_ADVERTENCIA:
                fill = fill_warn
            elif clasif == CLASIFICACION_VALIDO:
                fill = fill_ok
            if fill:
                for cell in ws[row_idx]:
                    cell.fill = fill

        anchos = [8, 24, 30, 16, 60, 50]
        for i, ancho in enumerate(anchos, start=1):
            ws.column_dimensions[chr(64 + i)].width = ancho

        ws.freeze_panes = 'A2'

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer
