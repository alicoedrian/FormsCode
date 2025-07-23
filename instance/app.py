from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
from functools import wraps
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import pytz
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = os.urandom(24) # ¡ADVERTENCIA! Revisa mis comentarios anteriores sobre la gestión de esta clave para producción.

# --- Configuración de la API de Epicor ---
EPICOR_API_TOKEN = "aW50ZWdyYXRpb246cjUwJEsyOHZhSUZpWXhhWQ=="
EPICOR_API_BASE_URL = "https://centralusdtapp73.epicorsaas.com/SaaS5333/api/v1/BaqSvc/HMP_ValidadorID/"

# --- Configuración de Google Sheets (General) ---
CREDS_FILE = 'contraseña.json'
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
TIMEZONE = 'America/Bogota' # Zona horaria de Bogotá, Colombia (UTC-5)

# --- Configuración ESPECÍFICA para las hojas de Google Sheets ---
RELACION_MEZCLAS_SPREADSHEET_ID = '1yF85f_to_zlnK5QSfeN-RipsjcSKy2VlRwDi6GPIni4'
RELACION_MEZCLAS_WORKSHEET_NAME = 'Relacion Mezcla'

SOLICITUD_CORES_SPREADSHEET_ID = '1knujlrctuhxz3xyBX667CKtOlDrCM26uLl68cabLMW0' # ID de tu hoja de Google Sheets de Cores
SOLICITUD_CORES_WORKSHEET_NAME = 'Requisición de cores' # Nombre exacto de tu pestaña de Cores

# --- Decorador para rutas que requieren inicio de sesión ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Funciones de Google Sheets ---

def get_sheet_connection(spreadsheet_id, worksheet_name):
    """Establece una conexión a una hoja de cálculo de Google Sheets.
       Esta función ahora será llamada solo una vez al inicio de la aplicación."""
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet.worksheet(worksheet_name)
    except Exception as e:
        print(f"Error al autenticar o abrir la hoja '{worksheet_name}' (ID: {spreadsheet_id}): {e}")
        app.logger.error(f"Error en get_sheet_connection: {e}", exc_info=True)
        return None

def validate_two_decimals(value_str):
    try:
        num_decimal = Decimal(value_str)
        num_places = abs(num_decimal.as_tuple().exponent)
        return num_places <= 2
    except InvalidOperation:
        return False

# --- FUNCIÓN DE FECHA ACTUALIZADA: Formato deseado 'D/MM/YYYY HH:MM:SS' ---
def get_formatted_datetime_string(dt_local):
    return dt_local.strftime("%#d/%m/%Y %H:%M:%S")


# --- CÓDIGO OPTIMIZADO: Conexión de Google Sheets al inicio de la aplicación ---
# Hacemos las conexiones a las hojas de cálculo una sola vez para mejorar el rendimiento.
# Esto evita la lentitud de autenticarse y conectarse en cada solicitud.
sheet_relacion_mezclas = get_sheet_connection(RELACION_MEZCLAS_SPREADSHEET_ID, RELACION_MEZCLAS_WORKSHEET_NAME)
sheet_solicitud_cores = get_sheet_connection(SOLICITUD_CORES_SPREADSHEET_ID, SOLICITUD_CORES_WORKSHEET_NAME)


# --- Rutas de Autenticación ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form.get('username')

        if not employee_id:
            flash('Por favor, ingresa tu ID de empleado.', 'warning')
            return redirect(url_for('login'))

        headers = {
            "Authorization": f"Basic {EPICOR_API_TOKEN}",
            "Content-Type": "application/json"
        }
        api_url = f"{EPICOR_API_BASE_URL}?ID={employee_id}"

        try:
            response = requests.get(api_url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                api_value = data.get('value', [])

                if api_value and isinstance(api_value, list) and len(api_value) > 0:
                    user_data = api_value[0]
                    emp_status = user_data.get('EmpBasic_EmpStatus')
                    emp_name = user_data.get('EmpBasic_Name', employee_id)

                    if emp_status == 'A':
                        session['user_id'] = user_data.get('EmpBasic_EmpID', employee_id)
                        session['user_name'] = emp_name
                        flash(f'Bienvenido, {emp_name}!', 'success')
                        next_url = request.form.get('next')
                        return redirect(next_url or url_for('home'))
                    elif emp_status in ['I', 'T']:
                        flash(f'El ID {employee_id} se encuentra bloqueado o inactivo.', 'danger')
                    else:
                        flash(f'Estado de empleado no reconocido ({emp_status}) para el ID {employee_id}.', 'warning')
                else:
                    flash(f'ID de empleado ({employee_id}) no encontrado.', 'danger')
            elif response.status_code == 401:
                flash('Error de autenticación con el servicio de validación.', 'danger')
            else:
                flash(f'Error al validar el ID ({response.status_code}). Intenta más tarde.', 'danger')
        except requests.exceptions.Timeout:
            app.logger.warning(f"Timeout al conectar con la API: {api_url}")
            flash('El servicio de validación tardó demasiado. Intenta más tarde.', 'danger')
        except requests.exceptions.RequestException as e:
            app.logger.error(f"Error de conexión a la API: {e}")
            flash('Error de conexión al servicio de validación. Intenta más tarde.', 'danger')
        return redirect(url_for('login', next=request.form.get('next')))

    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html', next=request.args.get('next'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# --- Ruta Principal del Dashboard (Home) ---
@app.route('/home')
# @login_required # Comentar/quitar si no se requiere login para esta página
def home():
    procesos = [
        {"nombre": "Extrusión", "url": url_for('proceso_extrusion_dashboard'), "icono": "fas fa-layer-group", "descripcion": "Formularios y estándares.", "color_icono": "#3498DB"},
        {"nombre": "Impresión", "url": url_for('proceso_impresion_dashboard'), "icono": "fas fa-print", "descripcion": "Formularios y estándares.", "color_icono": "#9B59B6"},
        {"nombre": "Laminación", "url": url_for('proceso_laminacion_dashboard'), "icono": "fas fa-clone", "descripcion": "Formularios y estándares.", "color_icono": "#F39C12"},
        {"nombre": "Corte", "url": url_for('proceso_corte_dashboard'), "icono": "fas fa-cut", "descripcion": "Formularios y estándares.", "color_icono": "#E74C3C"},
        {"nombre": "Sellado", "url": url_for('proceso_sellado_dashboard'), "icono": "fas fa-box-open", "descripcion": "Formularios y estándares.", "color_icono": "#2ECC71"},
        {"nombre": "Insertadoras", "url": url_for('proceso_insertadoras'), "icono": "fas fa-cogs", "descripcion": "Formularios y estándares.", "color_icono": "#34495E"},
    ]
    return render_template('home.html', username=session.get('user_name'), procesos=procesos)

# --- Formulario Compartido: Solicitud de Cores (AHORA UN FORMULARIO HTML PERSONALIZADO) ---
@app.route('/formulario/solicitud_cores', methods=['GET', 'POST'])
# @login_required # Mantén este decorador si quieres que esta página requiera login
def solicitud_cores_form():
    user_id_session = session.get('user_id')
    user_name_session = session.get('user_name')

    # Determinar el proceso de origen para la navegación de regreso
    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None
    if proceso_origen == 'impresion':
        url_volver_proceso = url_for('proceso_impresion_dashboard')
        proceso_origen_nombre = "Impresión"
    elif proceso_origen == 'laminacion':
        url_volver_proceso = url_for('proceso_laminacion_dashboard')
        proceso_origen_nombre = "Laminación"
    elif proceso_origen == 'corte':
        url_volver_proceso = url_for('proceso_corte_dashboard')
        proceso_origen_nombre = "Corte"
    elif proceso_origen == 'extrusion':
        url_volver_proceso = url_for('proceso_extrusion_dashboard')
        proceso_origen_nombre = "Extrusión"

    if request.method == 'POST':
        # 1. Recoger datos del formulario
        area_solicitante = request.form.get('area_solicitante')
        solicitante_id = request.form.get('solicitante_id')
        refiladora = request.form.get('refiladora')
        trabajo_ingresa = request.form.get('trabajo_ingresa')
        cantidad_cores_str = request.form.get('cantidad_cores')
        diametro = request.form.get('diametro')
        medida_mm_str = request.form.get('medida_mm')
        observaciones = request.form.get('observaciones') # No es obligatorio

        # 2. Validaciones
        errors = []

        if not area_solicitante:
            errors.append('Por favor, selecciona el Área que solicita.')
        
        if not solicitante_id:
            errors.append('Por favor, ingresa el ID de quien solicita.')
        elif not solicitante_id.isdigit() or len(solicitante_id) != 5:
            errors.append('El ID de quien solicita debe ser un número de 5 dígitos.')
            
        # Refiladora es condicional
        if area_solicitante == 'Corte': 
            if not refiladora:
                errors.append('Para el área de Corte, debes seleccionar una Refiladora.')
        
        if not trabajo_ingresa:
            errors.append('Por favor, ingresa el Trabajo Ingresa.')
        elif len(trabajo_ingresa) > 8:
            errors.append('El campo Trabajo Ingresa debe tener máximo 8 caracteres.')
            
        if not cantidad_cores_str:
            errors.append('Por favor, ingresa la Cantidad de cores.')
        else:
            try:
                cantidad_cores = int(cantidad_cores_str)
                if cantidad_cores <= 0:
                    errors.append('La cantidad de cores debe ser un número positivo.')
            except ValueError:
                errors.append('La cantidad de cores debe ser un número entero válido.')

        if not diametro:
            errors.append('Por favor, selecciona un Diámetro.')
            
        if not medida_mm_str:
            errors.append('Por favor, ingresa la Medida (mm).')
        else:
            try:
                medida_mm = int(medida_mm_str)
                if medida_mm <= 0:
                    errors.append('La Medida (mm) debe ser un número entero positivo.')
            except ValueError:
                errors.append('La Medida (mm) debe ser un número entero válido.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('shared_forms/solicitud_cores_form.html',
                                   username=user_name_session,
                                   subseccion="Solicitud de Cores",
                                   url_volver_proceso=url_volver_proceso,
                                   proceso_origen_nombre=proceso_origen_nombre,
                                   area_solicitante_val=area_solicitante,
                                   solicitante_id_val=solicitante_id,
                                   refiladora_val=refiladora,
                                   trabajo_ingresa_val=trabajo_ingresa,
                                   cantidad_cores_val=cantidad_cores_str,
                                   diametro_val=diametro,
                                   medida_mm_val=medida_mm_str,
                                   observaciones_val=observaciones)

        # 3. Usar la conexión a Google Sheets ya establecida
        sheet = sheet_solicitud_cores
        if sheet is None:
            flash('Error al conectar con la hoja de Google Sheets para Solicitud de Cores. Contacta a soporte (revisa IDs/nombres y permisos).', 'danger')
            return render_template('shared_forms/solicitud_cores_form.html',
                                   username=user_name_session,
                                   subseccion="Solicitud de Cores",
                                   url_volver_proceso=url_volver_proceso,
                                   proceso_origen_nombre=proceso_origen_nombre,
                                   area_solicitante_val=area_solicitante,
                                   solicitante_id_val=solicitante_id,
                                   refiladora_val=refiladora,
                                   trabajo_ingresa_val=trabajo_ingresa,
                                   cantidad_cores_val=cantidad_cores_str,
                                   diametro_val=diametro,
                                   medida_mm_val=medida_mm_str,
                                   observaciones_val=observaciones)

        try:
            bogota_tz = pytz.timezone(TIMEZONE)
            now_dt_bogota = datetime.now(bogota_tz)
            fecha_hora_para_sheets = get_formatted_datetime_string(now_dt_bogota)

            # Preparar los datos en el orden exacto de las columnas de Google Sheet
            row_data = [
                fecha_hora_para_sheets, # 1. Fecha y Hora
                area_solicitante,       # 2. Área que solicita
                solicitante_id,         # 3. ID de quien solicita
                refiladora if refiladora else 'N/A', # 4. Refiladora (si no aplica, 'N/A' en la hoja)
                trabajo_ingresa,        # 5. Trabajo ingresa
                cantidad_cores,         # 6. Cantidad de cores (ya es int)
                diametro,               # 7. Diámetro
                medida_mm,              # 8. Medida (mm) (ya es int)
                observaciones if observaciones else '' # 9. Observaciones (puede ser vacío)
            ]
            
            # --- LÓGICA CLAVE: BUSCAR LA ÚLTIMA FILA NO VACÍA EN LA COLUMNA A Y AÑADIR DESPUÉS ---
            # Esto soluciona el problema de que el registro se vaya a filas muy lejanas.
            column_a_values = sheet.col_values(1) # Obtener todos los valores de la columna A
            
            # Encontrar el índice de la última fila no vacía.
            # Recorremos la lista de atrás hacia adelante para encontrar el último valor no vacío.
            last_row_index_in_A = len(column_a_values)
            while last_row_index_in_A > 0 and not column_a_values[last_row_index_in_A - 1].strip():
                last_row_index_in_A -= 1
            
            # La fila para la nueva inserción es la última fila no vacía + 1.
            insert_row_position = last_row_index_in_A + 1
            
            # Insertar la nueva fila en la posición calculada.
            sheet.insert_row(row_data, insert_row_position, value_input_option='USER_ENTERED')
            
            # --- NUEVA LÓGICA: Copiar formato de las celdas J a la S (índices 9 a 18) ---
            # La fila de origen para copiar el formato es la que acabamos de insertar sobre.
            # Si el registro anterior está en la fila 3790, insertamos en 3791.
            # El formato a copiar está en la fila 3790.
            source_row_for_format = insert_row_position + 1
            
            # Solo copiamos el formato si existe una fila de origen válida (que no sea el encabezado)
            if source_row_for_format > 2:
                try:
                    # Definir el rango de origen (ej. 'J3790:S3790')
                    source_range = f'J{source_row_for_format}:S{source_row_for_format}'
                    # Definir el rango de destino (ej. 'J3791:S3791')
                    destination_range_start_cell = f'J{insert_row_position}'
                    
                    # Usar copy_range para copiar solo el formato
                    sheet.copy_range(
                        src_range=source_range,
                        dst_range=destination_range_start_cell,
                        paste_type='FORMAT'
                    )
                    app.logger.info(f"Formato copiado de {source_range} a {destination_range_start_cell} en la hoja de cores.")
                except Exception as format_e:
                    # Registra el error de formato, pero no detengas el flujo principal.
                    app.logger.error(f"Error al copiar el formato en la hoja de cores: {format_e}", exc_info=True)
                    # No flasheamos un mensaje de error al usuario por un problema de formato.

            flash('¡Solicitud de Cores enviada exitosamente!', 'success')
            return redirect(url_for('solicitud_cores_form', origen=proceso_origen))
        except Exception as e:
            app.logger.error(f"Error al añadir datos a la hoja de Solicitud de Cores: {e}", exc_info=True)
            flash(f'Error al guardar la solicitud: {e}. Contacta a soporte técnico.', 'danger')
            return render_template('shared_forms/solicitud_cores_form.html',
                                   username=user_name_session,
                                   subseccion="Solicitud de Cores",
                                   url_volver_proceso=url_volver_proceso,
                                   proceso_origen_nombre=proceso_origen_nombre,
                                   area_solicitante_val=area_solicitante,
                                   solicitante_id_val=solicitante_id,
                                   refiladora_val=refiladora,
                                   trabajo_ingresa_val=trabajo_ingresa,
                                   cantidad_cores_val=cantidad_cores_str,
                                   diametro_val=diametro,
                                   medida_mm_val=medida_mm_str,
                                   observaciones_val=observaciones)

    # Si la solicitud es GET (o después de un error de POST que redirige con GET),
    # renderizamos el formulario. Usamos request.args.get para repoblar si hay parámetros en la URL
    return render_template('shared_forms/solicitud_cores_form.html',
                           username=session.get('user_name'),
                           subseccion="Solicitud de Cores",
                           url_volver_proceso=url_volver_proceso,
                           proceso_origen_nombre=proceso_origen_nombre,
                           area_solicitante_val=request.args.get('area_solicitante_val'),
                           solicitante_id_val=request.args.get('solicitante_id_val'),
                           refiladora_val=request.args.get('refiladora_val'),
                           trabajo_ingresa_val=request.args.get('trabajo_ingresa_val'),
                           cantidad_cores_val=request.args.get('cantidad_cores_val'),
                           diametro_val=request.args.get('diametro_val'),
                           medida_mm_val=request.args.get('medida_mm_val'),
                           observaciones_val=request.args.get('observaciones_val'))


# --- Google Sheet Compartido: Monitoreo de Cores (Actualizado para mostrar datos) ---
@app.route('/sheet/monitoreo_cores')
@login_required # Mantén este decorador si quieres que esta página requiera login
def monitoreo_cores_sheet():
    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None

    if proceso_origen == 'impresion':
        url_volver_proceso = url_for('proceso_impresion_dashboard')
        proceso_origen_nombre = "Impresión"
    elif proceso_origen == 'laminacion':
        url_volver_proceso = url_for('proceso_laminacion_dashboard')
        proceso_origen_nombre = "Laminación"
    elif proceso_origen == 'corte':
        url_volver_proceso = url_for('proceso_corte_dashboard')
        proceso_origen_nombre = "Corte"
    elif proceso_origen == 'extrusion':
        url_volver_proceso = url_for('proceso_extrusion_dashboard')
        proceso_origen_nombre = "Extrusión"

    # --- Lógica para obtener datos de Google Sheets ---
    # Usamos la conexión global sheet_solicitud_cores para el monitoreo también
    sheet = sheet_solicitud_cores
    all_records = []
    headers = []

    if sheet is None:
        flash('No se pudo establecer conexión con la hoja de Google Sheets para el monitoreo de cores. Contacta a soporte.', 'danger')
        return render_template('shared_forms/monitoreo_cores.html',
                               username=session.get('user_name'),
                               url_volver_proceso=url_volver_proceso,
                               proceso_origen_nombre=proceso_origen_nombre,
                               subseccion="Monitoreo de Estado de Core",
                               records=[], # Lista vacía si hay error
                               headers=[]) # Lista vacía si hay error

    try:
        # Obtener todos los valores de la hoja
        all_values = sheet.get_all_values()
        if all_values:
            headers = all_values[0] # La primera fila son los encabezados
            # Los registros comienzan desde la segunda fila, y los revertimos para mostrar el último primero
            all_records = all_values[1:]
            all_records.reverse() # Invertir la lista para mostrar el último registro de primero
            
            # Opcional: limitar a las columnas A a S (índices 0 a 18)
            all_records_filtered = []
            for row in all_records:
                # Asegurarse de que la fila tenga al menos 19 elementos antes de intentar cortar
                if len(row) > 18:
                    all_records_filtered.append(row[0:19]) 
                else:
                    all_records_filtered.append(row + [''] * (19 - len(row))) # Rellenar con vacíos si es más corta
            all_records = all_records_filtered

            headers_filtered = headers[0:19] # Filtrar también los encabezados
            # Si los encabezados son menos de 19, rellenar con vacíos
            if len(headers_filtered) < 19:
                headers_filtered += [''] * (19 - len(headers_filtered))
            headers = headers_filtered

        else:
            flash('La hoja de cálculo está vacía.', 'info')
    except Exception as e:
        app.logger.error(f"Error al leer datos de la hoja de monitoreo de cores: {e}", exc_info=True)
        flash('Error al cargar los datos del monitoreo de cores. Por favor, intenta más tarde.', 'danger')


    return render_template('shared_forms/monitoreo_cores.html',
                           username=session.get('user_name'),
                           url_volver_proceso=url_volver_proceso,
                           proceso_origen_nombre=proceso_origen_nombre,
                           subseccion="Monitoreo de Estado de Core",
                           records=all_records, # Pasar los datos a la plantilla
                           headers=headers) # Pasar los encabezados a la plantilla


# --- Rutas Específicas por Proceso ---

# Extrusión (Placeholder - En desarrollo)
@app.route('/proceso/extrusion')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_extrusion_dashboard():
    opciones = [
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='extrusion'), "icono": "fas fa-tape", "descripcion": "Realizar nueva solicitud."},
        {"nombre": "Monitoreo de Cores", "url": url_for('monitoreo_cores_sheet', origen='extrusion'), "icono": "fas fa-tasks", "descripcion": "Ver estado actual."},
    ]
    flash("La sección de Extrusión está en desarrollo. ¡Vuelve pronto!", "info")
    return render_template('processes/extrusion/extrusion_dashboard.html',
                           username=session.get('user_name'), opciones=opciones, nombre_proceso="Extrusión")

# Impresión (Placeholder - En desarrollo)
@app.route('/proceso/impresion')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_impresion_dashboard():
    opciones = [
        {"nombre": "Formulario Ambiental", "url": url_for('proceso_impresion_form_ambiental'), "icono": "fas fa-leaf", "descripcion": "Control de aspectos ambientales."},
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='impresion'), "icono": "fas fa-tape", "descripcion": "Realizar nueva solicitud."},
        {"nombre": "Monitoreo de Cores", "url": url_for('monitoreo_cores_sheet', origen='impresion'), "icono": "fas fa-tasks", "descripcion": "Ver estado actual."},
    ]
    flash("La sección de Impresión está en desarrollo. ¡Vuelve pronto!", "info")
    return render_template('processes/impresion/impresion_dashboard.html',
                           username=session.get('user_name'), opciones=opciones, nombre_proceso="Impresión")

@app.route('/proceso/impresion/formulario_ambiental')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_impresion_form_ambiental():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSdtB1HUXrQz7e5EfO_aKSUi-11bqCnT96_pf2ZR0kE9n8wvoQ/viewform?embedded=true"
    return render_template('processes/impresion/impresion_form_ambiental.html',
                           username=session.get('user_name'), nombre_proceso="Impresión",
                           subseccion="Formulario Ambiental", formulario_url=formulario_url,
                           url_volver=url_for('proceso_impresion_dashboard'))

# Laminación (¡Aquí integramos el nuevo formulario HTML personalizado!)
@app.route('/proceso/laminacion')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_laminacion_dashboard():
    opciones = [
        {"nombre": "Relación de Mezclas", "url": url_for('proceso_laminacion_form_mezclas'), "icono": "fas fa-flask", "descripcion": "Formularios y estándares."},
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='laminacion'), "icono": "fas fa-tape", "descripcion": "Realizar nueva solicitud."},
        {"nombre": "Monitoreo de Cores", "url": url_for('monitoreo_cores_sheet', origen='laminacion'), "icono": "fas fa-tasks", "descripcion": "Ver estado actual."},
    ]
    return render_template('processes/laminacion/laminacion_dashboard.html',
                           username=session.get('user_name'), opciones=opciones, nombre_proceso="Laminación")

# --- RUTA Y LÓGICA PARA EL NUEVO FORMULARIO HTML DE RELACIÓN DE MEZCLAS ---
@app.route('/proceso/laminacion/relacion_mezclas', methods=['GET', 'POST'])
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_laminacion_form_mezclas():
    user_id_session = session.get('user_id')
    user_name_session = session.get('user_name')

    if request.method == 'POST':
        maquina = request.form.get('maquina')
        turno = request.form.get('turno')
        operario_responsable = request.form.get('operario_responsable')
        peso_adhesivo_str = request.form.get('peso_adhesivo')
        peso_correactante_str = request.form.get('peso_correactante')
        relacion_mezcla_str = request.form.get('relacion_mezcla')

        # --- Validación básica de datos requeridos ---
        if not all([maquina, turno, operario_responsable, peso_adhesivo_str, peso_correactante_str, relacion_mezcla_str]):
            flash('Por favor, completa todos los campos requeridos.', 'danger')
            return render_template('processes/laminacion/laminacion_form_mezclas.html',
                                   username=user_name_session, nombre_proceso="Laminación",
                                   subseccion="Relación de Mezclas", url_volver=url_for('proceso_laminacion_dashboard'),
                                   maquina_val=maquina, turno_val=turno, operario_responsable_val=operario_responsable,
                                   peso_adhesivo_val=peso_adhesivo_str, peso_correactante_val=peso_correactante_str, relacion_mezcla_val=relacion_mezcla_str)

        # --- Validación y conversión de campos numéricos ---
        try:
            # Validar que los valores sean convertibles a float y no negativos
            peso_adhesivo_float = float(peso_adhesivo_str)
            peso_correactante_float = float(peso_correactante_str)
            relacion_mezcla_float = float(relacion_mezcla_str)

            if peso_adhesivo_float < 0 or peso_correactante_float < 0 or relacion_mezcla_float < 0:
                flash('Los campos de peso y relación no pueden ser negativos.', 'danger')
                raise ValueError("Valores negativos detectados.")

            # --- VALIDACIÓN FINAL: Permitir solo 2 decimales usando validate_two_decimals ---
            print(f"Validando peso_adhesivo_str: '{peso_adhesivo_str}', Result: {validate_two_decimals(peso_adhesivo_str)}")
            print(f"Validando peso_correactante_str: '{peso_correactante_str}', Result: {validate_two_decimals(peso_correactante_str)}")
            print(f"Validando relacion_mezcla_str: '{relacion_mezcla_str}', Result: {validate_two_decimals(relacion_mezcla_str)}")

            if not (validate_two_decimals(peso_adhesivo_str) and
                    validate_two_decimals(peso_correactante_str) and
                    validate_two_decimals(relacion_mezcla_str)):
                print(">>> MÁS DE 2 DECIMALES DETECTADOS EN ALGÚN CAMPO <<<") # Debug print
                flash('Los campos de peso y relación solo permiten hasta 2 decimales después del punto.', 'danger')
                raise ValueError("Más de 2 decimales detectados.")

            # --- NUEVO CÁLCULO Y ALERTA DE RELACIÓN DE MEZCLAS ---
            if peso_correactante_float == 0:
                flash('No se puede calcular la relación de mezcla: el peso correactante no puede ser cero.', 'warning')

                print("Advertencia: Peso correactante es cero.")
            else:
                relacion_calculada = peso_adhesivo_float / peso_correactante_float
                # Redondea el valor calculado a 2 decimales para la comparación,
                relacion_calculada_redondeada = round(relacion_calculada, 2)

                print(f"Relación calculada: {relacion_calculada_redondeada}")

                if 1.23 <= relacion_calculada_redondeada <= 1.32:
                    flash('TENER CUIDADO CON LA RELACIÓN DE MEZCLAS', 'warning')
                    print("ALERTA: CUIDADO CON LA RELACIÓN DE MEZCLAS.")
            # --- FIN CÁLCULO Y ALERTA ---

        except ValueError as e:
            print(f"Error de validación o conversión capturado en except block: {e}")
            return render_template('processes/laminacion/laminacion_form_mezclas.html',
                                   username=user_name_session, nombre_proceso="Laminación",
                                   subseccion="Relación de Mezclas", url_volver=url_for('proceso_laminacion_dashboard'),
                                   maquina_val=maquina, turno_val=turno, operario_responsable_val=operario_responsable,
                                   peso_adhesivo_val=peso_adhesivo_str, peso_correactante_val=peso_correactante_str, relacion_mezcla_val=relacion_mezcla_str)


        # --- Conectar a Google Sheets y añadir datos ---
        # Usamos la conexión global sheet_relacion_mezclas para mejorar el rendimiento
        sheet = sheet_relacion_mezclas
        if sheet is None:
            flash('Error al conectar con la hoja de Google Sheets. Contacta a soporte (revisa IDs/nombres y permisos).', 'danger')
            return render_template('processes/laminacion/laminacion_form_mezclas.html',
                                   username=user_name_session, nombre_proceso="Laminación",
                                   subseccion="Relación de Mezclas", url_volver=url_for('proceso_laminacion_dashboard'),
                                   maquina_val=maquina, turno_val=turno, operario_responsable_val=operario_responsable,
                                   peso_adhesivo_val=peso_adhesivo_str, peso_correactante_val=peso_correactante_str, relacion_mezcla_val=relacion_mezcla_str)

        try:
            bogota_tz = pytz.timezone(TIMEZONE)
            now_dt_bogota = datetime.now(bogota_tz)


            fecha_hora_para_sheets = get_formatted_datetime_string(now_dt_bogota)


            row_data = [
                fecha_hora_para_sheets, # Es la cadena con el formato D/MM/YYYY HH:MM:SS
                maquina,
                turno,
                operario_responsable,
                peso_adhesivo_float,
                peso_correactante_float,
                relacion_mezcla_float,
                user_id_session, # Se incluye el ID de usuario
                user_name_session # Se incluye el nombre de usuario
            ]

            # Añadir al final del último resultado
            sheet.append_row(row_data, value_input_option='USER_ENTERED')

            flash('¡Información de Relación de Mezclas guardada exitosamente!', 'success')
            return redirect(url_for('proceso_laminacion_dashboard'))

        except Exception as e:
            app.logger.error(f"Error al añadir datos a la hoja de Relación de Mezclas: {e}", exc_info=True)
            flash(f'Error al guardar la información: {e}. Contacta a soporte técnico.', 'danger')
            return render_template('processes/laminacion/laminacion_form_mezclas.html',
                                   username=user_name_session, nombre_proceso="Laminación",
                                   subseccion="Relación de Mezclas", url_volver=url_for('proceso_laminacion_dashboard'),
                                   maquina_val=maquina, turno_val=turno, operario_responsable_val=operario_responsable,
                                   peso_adhesivo_val=peso_adhesivo_str, peso_correactante_val=peso_correactante_str, relacion_mezcla_val=relacion_mezcla_str)

    # Si la solicitud es GET, simplemente renderizamos el formulario
    return render_template('processes/laminacion/laminacion_form_mezclas.html',
                           username=user_name_session, nombre_proceso="Laminación",
                           subseccion="Relación de Mezclas", url_volver=url_for('proceso_laminacion_dashboard'),
                           maquina_val=None, turno_val=None, operario_responsable_val=None,
                           peso_adhesivo_val=None, peso_correactante_val=None, relacion_mezcla_val=None)


# Corte (Placeholder - En desarrollo)
@app.route('/proceso/corte')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_corte_dashboard():
    opciones = [
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='corte'), "icono": "fas fa-tape", "descripcion": "Realizar nueva solicitud."},
        {"nombre": "Monitoreo de Cores", "url": url_for('monitoreo_cores_sheet', origen='corte'), "icono": "fas fa-tasks", "descripcion": "Ver estado actual."},
    ]
    flash("La sección de Corte está en desarrollo. ¡Vuelve pronto!", "info")
    return render_template('processes/corte/corte_dashboard.html',
                           username=session.get('user_name'), opciones=opciones, nombre_proceso="Corte")

# Sellado (Placeholder - En desarrollo)
@app.route('/proceso/sellado')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_sellado_dashboard():
    opciones = [
        {"nombre": "Estándares de Máquina", "url": url_for('proceso_sellado_form_estandares'), "icono": "fas fa-cogs", "descripcion": "Consulta de parámetros estándar."},
    ]
    flash("La sección de Sellado está en desarrollo. ¡Vuelve pronto!", "info")
    return render_template('processes/sellado/sellado_dashboard.html',
                           username=session.get('user_name'), opciones=opciones, nombre_proceso="Sellado")

@app.route('/proceso/sellado/estandares_maquina')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_sellado_form_estandares():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSeJtdN1LxC0kd0HjCBEjaaMBHNXiF02H_tBdmE-4JokmswvkQ/viewform?embedded=true"
    return render_template('processes/sellado/sellado_form_estandares.html',
                           username=session.get('user_name'), nombre_proceso="Sellado",
                           subseccion="Formulario Ambiental", formulario_url=formulario_url,
                           url_volver=url_for('proceso_sellado_dashboard'))

# Insertadoras (Placeholder - En desarrollo)
@app.route('/proceso/insertadoras')
# @login_required # Comentar/quitar si no se requiere login para esta página
def proceso_insertadoras():
    flash("La sección de Insertadoras está en desarrollo. ¡Vuelve pronto!", "info")
    return redirect(url_for('home'))


# --- Manejadores de errores ---
@app.errorhandler(404)
def page_not_found(e):
    user_logged_in = 'user_id' in session
    flash("La página que buscas no existe (Error 404).", "warning")
    return redirect(url_for('home' if user_logged_in else 'login'))

@app.errorhandler(500)
def internal_server_error(e):
    user_logged_in = 'user_id' in session
    app.logger.error(f"Error interno del servidor: {e}", exc_info=True)
    flash("Ocurrió un error interno en el servidor (Error 500). Por favor, intenta más tarde.", "danger")
    return redirect(url_for('home' if user_logged_in else 'login'))

# --- Punto de entrada para ejecutar la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)