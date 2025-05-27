from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from functools import wraps
import requests

app = Flask(__name__)

app.secret_key = os.urandom(24)

# --- Configuración de la API de Epicor ---
EPICOR_API_TOKEN = "aW50ZWdyYXRpb246cjUwJEsyOHZhSUZpWXhhWQ==" 
EPICOR_API_BASE_URL = "https://centralusdtapp73.epicorsaas.com/SaaS5333/api/v1/BaqSvc/HMP_ValidadorID/"


def login_required(f):
    @wraps(f) 
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas de Autenticación ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        employee_id = request.form.get('username') # El campo 'username' es el ID del empleado

        if not employee_id:
            flash('Por favor, ingresa tu ID de empleado.', 'warning')
            return redirect(url_for('login'))

        headers = {
            "Authorization": f"Basic {EPICOR_API_TOKEN}",
            "Content-Type": "application/json"
        }
        api_url = f"{EPICOR_API_BASE_URL}?ID={employee_id}"

        try:
            response = requests.get(api_url, headers=headers, timeout=10) # Timeout de 10 segundos

            if response.status_code == 200:
                data = response.json()
                api_value = data.get('value', [])

                if api_value and isinstance(api_value, list) and len(api_value) > 0:
                    user_data = api_value[0] # Tomamos el primer resultado
                    emp_status = user_data.get('EmpBasic_EmpStatus')
                    emp_name = user_data.get('EmpBasic_Name', employee_id) # Usar ID si el nombre no viene

                    if emp_status == 'A': # Activo
                        session['user_id'] = user_data.get('EmpBasic_EmpID', employee_id)
                        session['user_name'] = emp_name
                        flash(f'Bienvenido, {emp_name}!', 'success')
                        next_url = request.form.get('next')
                        return redirect(next_url or url_for('home'))
                    elif emp_status in ['I', 'T']: # Inactivo o Terminado
                        flash(f'El ID {employee_id} se encuentra bloqueado o inactivo. Contacta al administrador.', 'danger')
                    else:
                        flash(f'Estado de empleado no reconocido ({emp_status}) para el ID {employee_id}.', 'warning')
                else:
                    flash(f'ID de empleado ({employee_id}) no encontrado en el sistema.', 'danger')
            elif response.status_code == 401: # No autorizado
                flash('Error de autenticación con el servicio de validación. Contacta al administrador.', 'danger')
            else: # Otros errores de la API
                flash(f'Error al validar el ID ({response.status_code}). Por favor, intenta más tarde.', 'danger')

        except requests.exceptions.Timeout:
            app.logger.error(f"Timeout al conectar con la API: {api_url}")
            flash('El servicio de validación tardó demasiado en responder. Intenta más tarde.', 'danger')
        except requests.exceptions.RequestException as e: # Otros errores de requests (conexión, etc.)
            app.logger.error(f"Error de conexión a la API: {e}")
            flash('Error de conexión al servicio de validación. Intenta más tarde.', 'danger')

        return redirect(url_for('login', next=request.form.get('next')))

    if 'user_id' in session: # Si ya está en sesión, va al home
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
@login_required
def home():
    procesos = [
        {"nombre": "Extrusión", "url": url_for('proceso_extrusion_dashboard'), "icono": "fas fa-layer-group", "descripcion": "Gestión de parámetros y calidad del film.", "color_icono": "#3498DB"},
        {"nombre": "Impresión", "url": url_for('proceso_impresion_dashboard'), "icono": "fas fa-print", "descripcion": "Formularios, estándares y control de calidad.", "color_icono": "#9B59B6"},
        {"nombre": "Laminación", "url": url_for('proceso_laminacion_dashboard'), "icono": "fas fa-clone", "descripcion": "Control de adhesivos y unión de materiales.", "color_icono": "#F39C12"},
        {"nombre": "Corte", "url": url_for('proceso_corte_dashboard'), "icono": "fas fa-cut", "descripcion": "Configuración de medidas y calidad de bordes.", "color_icono": "#E74C3C"},
        {"nombre": "Sellado", "url": url_for('proceso_sellado_dashboard'), "icono": "fas fa-box-open", "descripcion": "Parámetros, calidad y documentación de confección.", "color_icono": "#2ECC71"},
        {"nombre": "Insertadoras", "url": url_for('proceso_insertadoras'), "icono": "fas fa-cogs", "descripcion": "Manejo de accesorios y procesos auxiliares.", "color_icono": "#34495E"},
    ]
    return render_template('home.html', username=session.get('user_name'), procesos=procesos)

# --- Formulario Compartido: Solicitud de Cores ---
@app.route('/formulario/solicitud_cores')
@login_required
def solicitud_cores_form():

    formulario_url_cores = "https://docs.google.com/forms/d/1Jw6s_pOFvPMIwQLX2qNZniRReR8F7563E3lD_VynzKM/viewform?edit_requested=true" # ¡VERIFICA ESTA URL!

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
    # Añade más procesos aquí si es necesario

    return render_template('shared_forms/solicitud_cores.html',
                           username=session.get('user_name'),
                           formulario_url=formulario_url_cores,
                           url_volver_proceso=url_volver_proceso,
                           proceso_origen_nombre=proceso_origen_nombre,
                           subseccion="Solicitud de Cores")

# --- Rutas Específicas del Proceso de Extrusión ---
@app.route('/proceso/extrusion')
@login_required
def proceso_extrusion_dashboard():
    opciones_extrusion = [
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='extrusion'), "icono": "fas fa-tape", "descripcion": "Realizar una nueva solicitud de cores."},
        {"nombre": "Parámetros de Extrusión", "url": "#", "icono": "fas fa-thermometer-half", "descripcion": "Registro de parámetros (en desarrollo)."},
    ]
    return render_template('processes/extrusion/extrusion_dashboard.html',
                           username=session.get('user_name'),
                           opciones=opciones_extrusion,
                           nombre_proceso="Extrusión")

# --- Rutas Específicas del Proceso de Impresión ---
@app.route('/proceso/impresion')
@login_required
def proceso_impresion_dashboard():
    opciones_impresion = [
        {"nombre": "Formulario Ambiental", "url": url_for('proceso_impresion_form_ambiental'), "icono": "fas fa-leaf", "descripcion": "Registro y control de aspectos ambientales."},
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='impresion'), "icono": "fas fa-tape", "descripcion": "Realizar una nueva solicitud de cores."},
        {"nombre": "SOPs", "url": "#", "icono": "fas fa-file-alt", "descripcion": "Procedimientos Operativos Estándar (en desarrollo)."},
        {"nombre": "Control de Calidad", "url": "#", "icono": "fas fa-check-circle", "descripcion": "Documentos y guías de calidad (en desarrollo)."},
    ]
    return render_template('processes/impresion/impresion_dashboard.html',
                           username=session.get('user_name'),
                           opciones=opciones_impresion,
                           nombre_proceso="Impresión")

@app.route('/proceso/impresion/formulario_ambiental')
@login_required
def proceso_impresion_form_ambiental():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSdtB1HUXrQz7e5EfO_aKSUi-11bqCnT96_pf2ZR0kE9n8wvoQ/viewform?embedded=true"
    return render_template('processes/impresion/impresion_form_ambiental.html',
                           username=session.get('user_name'),
                           nombre_proceso="Impresión",
                           subseccion="Formulario Ambiental",
                           formulario_url=formulario_url,
                           url_volver=url_for('proceso_impresion_dashboard'))

# --- Rutas Específicas del Proceso de Laminación ---
@app.route('/proceso/laminacion')
@login_required
def proceso_laminacion_dashboard():
    opciones_laminacion = [
        {"nombre": "Relación de Mezclas", "url": url_for('proceso_laminacion_form_mezclas'), "icono": "fas fa-flask", "descripcion": "Registro y consulta de la relación de mezclas."},
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='laminacion'), "icono": "fas fa-tape", "descripcion": "Realizar una nueva solicitud de cores."},
        {"nombre": "Parámetros de Máquina", "url": "#", "icono": "fas fa-sliders-h", "descripcion": "Configuración y estándares (en desarrollo)."},
    ]
    return render_template('processes/laminacion/laminacion_dashboard.html',
                           username=session.get('user_name'),
                           opciones=opciones_laminacion,
                           nombre_proceso="Laminación")

@app.route('/proceso/laminacion/relacion_mezclas')
@login_required
def proceso_laminacion_form_mezclas():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSc9nVd95J8Wo_GVE9IEvBntoWTXX8chP1COSjhsy66g8CQdBw/viewform?embedded=true"
    return render_template('processes/laminacion/laminacion_form_mezclas.html',
                           username=session.get('user_name'),
                           nombre_proceso="Laminación",
                           subseccion="Relación de Mezclas",
                           formulario_url=formulario_url,
                           url_volver=url_for('proceso_laminacion_dashboard'))

# --- Rutas Específicas del Proceso de Corte ---
@app.route('/proceso/corte')
@login_required
def proceso_corte_dashboard():
    opciones_corte = [
        {"nombre": "Solicitud de Cores", "url": url_for('solicitud_cores_form', origen='corte'), "icono": "fas fa-tape", "descripcion": "Realizar una nueva solicitud de cores."},
        {"nombre": "Especificaciones de Corte", "url": "#", "icono": "fas fa-ruler-combined", "descripcion": "Formatos y guías de corte (en desarrollo)."},
    ]
    return render_template('processes/corte/corte_dashboard.html',
                           username=session.get('user_name'),
                           opciones=opciones_corte,
                           nombre_proceso="Corte")

# --- Rutas Específicas del Proceso de Sellado ---
@app.route('/proceso/sellado')
@login_required
def proceso_sellado_dashboard():
    opciones_sellado = [
        {"nombre": "Estándares de Máquina", "url": url_for('proceso_sellado_form_estandares'), "icono": "fas fa-cogs", "descripcion": "Registro y consulta de parámetros estándar de máquinas."},
        {"nombre": "Control de Calidad", "url": "#", "icono": "fas fa-clipboard-check", "descripcion": "Formatos y guías de calidad para sellado (en desarrollo)."},
        
    ]
    return render_template('processes/sellado/sellado_dashboard.html',
                           username=session.get('user_name'),
                           opciones=opciones_sellado,
                           nombre_proceso="Sellado")

@app.route('/proceso/sellado/estandares_maquina')
@login_required
def proceso_sellado_form_estandares():
    formulario_url_sellado = "https://docs.google.com/forms/d/e/1FAIpQLSeJtdN1LxC0kd0HjCBEjaaMBHNXiF02H_tBdmE-4JokmswvkQ/viewform?embedded=true"
    return render_template('processes/sellado/sellado_form_estandares.html',
                           username=session.get('user_name'),
                           nombre_proceso="Sellado",
                           subseccion="Estándares de Máquina",
                           formulario_url=formulario_url_sellado,
                           url_volver=url_for('proceso_sellado_dashboard'))

# --- Ruta Placeholder para Insertadoras ---
@app.route('/proceso/insertadoras')
@login_required
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
    flash("Ocurrió un error interno en el servidor (Error 500). Por favor, intenta más tarde o contacta al administrador.", "danger")
    return redirect(url_for('home' if user_logged_in else 'login'))

# --- Punto de entrada para ejecutar la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)