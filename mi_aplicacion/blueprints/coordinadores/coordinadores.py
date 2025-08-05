from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app, jsonify # Añadir jsonify aquí
)
import os
from functools import wraps
import json

# IMPORTAR LA API DE MONITOREO DE CUCHILLAS (ruta relativa correcta)
# Asegúrate de que monitoreo_cuchillas_api.py exista en la misma carpeta que coordinadores.py
from .monitoreo_cuchillas_api import get_pending_monitoreo_cuchillas_for_approval, update_monitoreo_cuchillas_record


# --- Configuración del Blueprint ---
coordinadores_bp = Blueprint('coordinadores', __name__,
                             # ATENCIÓN: AJUSTA ESTA RUTA DE TEMPLATE_FOLDER SEGÚN TU ESTRUCTURA REAL
                             # Si '../../../templates' te funciona, déjalo así.
                             # Si tu estructura es mi_aplicacion/templates, entonces usa '../../templates'
                             template_folder='../../templates', # Probablemente esta sea la correcta
                             static_folder='../../static',     # Probablemente esta sea la correcta
                             url_prefix='/coordinadores')

# --- Función auxiliar para limpiar la sesión del coordinador ---
def _clear_coordinador_session():
    """Limpia todas las variables de sesión relacionadas con el coordinador."""
    session.pop('coordinador_access_validated', None)
    session.pop('coordinador_role', None)
    session.pop('coordinador_user_id', None)
    session.pop('coordinador_employee_id', None)
    session.pop('coordinador_username', None)
    session.permanent = False # Asegurar que la sesión NO sea permanente
    # session.modified = True # Forzar a Flask a guardar la sesión si pop no lo hace implícitamente

# --- Decorador para asegurar validación al entrar ---
def validation_required_coordinador(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('coordinador_access_validated'):
            flash('Debes validar tu carnet para acceder a este módulo.', 'warning')
            return redirect(url_for('coordinadores.coordinadores_entry', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Decorador para verificar rol ---
def role_required_coordinador(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Si no está validado O el rol no es permitido, limpiar sesión y redirigir
            if not session.get('coordinador_access_validated') or session.get('coordinador_role') not in allowed_roles:
                flash('No tienes los permisos necesarios para acceder a esta sección o tu acceso ha expirado.', 'danger')
                _clear_coordinador_session() # Limpiar la sesión si el rol no es válido
                return redirect(url_for('coordinadores.coordinadores_entry'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Rutas para el Módulo de Coordinadores ---

@coordinadores_bp.route('/entry', methods=['GET', 'POST'])
def coordinadores_entry():
    if request.method == 'GET':
        if session.get('coordinador_access_validated'):
            # independientemente de si ya estaba validado, entonces:
            _clear_coordinador_session() # Siempre limpiar para forzar re-entrada

    if request.method == 'POST':
        carnet_id = request.form.get('employee_id')
        next_url = request.form.get('next')

        if not carnet_id:
            flash('El número de carnet es requerido.', 'warning')
            return render_template('coordinadores/coordinadores_entry.html',
                                   nombre_proceso="Coordinadores de Verificación",
                                   subseccion="Acceso al Módulo",
                                   next=next_url)

        json_file_path = os.path.join(coordinadores_bp.root_path, 'allowed_carnets.json')

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                allowed_carnets_data = json.load(f)

            allowed_carnets_list = allowed_carnets_data.get('allowed_carnets', [])

            carnet_str = str(carnet_id)

            if carnet_str in allowed_carnets_list:
                session['coordinador_access_validated'] = True
                session['coordinador_role'] = 'coordinator' # Asignar un rol por defecto

                # --- CAMBIO CLAVE AQUÍ ---
                # Usar el user_id y user_name de la sesión principal para el coordinador
                # Esto asegura que aparezca el usuario logueado inicialmente
                session['coordinador_user_id'] = session.get('user_id', carnet_str) # Prioriza el user_id de la sesión principal. Si no existe, usa el carnet.
                session['coordinador_username'] = session.get('user_name', 'Coordinador de Verificación') # Prioriza el nombre de la sesión principal. Si no existe, usa un fallback.
                                
                # Mantener coordinador_employee_id como el carnet usado para la validación del módulo.
                # Este ID es el que se validó para el acceso al módulo de coordinadores.
                session['coordinador_employee_id'] = carnet_str
                # --- FIN DEL CAMBIO CLAVE ---

                # Aseguramos que esta parte de la sesión NO sea permanente, para que expire
                # al cerrar el navegador o explícitamente.
                session.permanent = False

                return redirect(next_url or url_for('coordinadores.coordinadores_dashboard'))
            else:
                flash('Carnet no autorizado para este módulo.', 'danger')
                _clear_coordinador_session() # Limpiar la sesión en caso de validación fallida
                current_app.logger.warning(f"Intento de validación fallido para carnet: {carnet_str}. No autorizado en allowed_carnets.json")

        except FileNotFoundError:
            flash('Error de configuración: El archivo de carnets autorizados no se encontró. Contacta a soporte.', 'danger')
            current_app.logger.error(f"Archivo JSON de carnets no encontrado en: {json_file_path}")
            _clear_coordinador_session()
        except json.JSONDecodeError:
            flash('Error de configuración: El archivo de carnets autorizados no es un JSON válido. Contacta a soporte.', 'danger')
            current_app.logger.error(f"Error al decodificar JSON en: {json_file_path}")
            _clear_coordinador_session()
        except Exception as e:
            flash('Ocurrió un error inesperado al validar el carnet. Intenta de nuevo o contacta a soporte.', 'danger')
            current_app.logger.error(f"Error general al validar carnet con JSON: {e}", exc_info=True)
            _clear_coordinador_session()

    return render_template('coordinadores/coordinadores_entry.html',
                           nombre_proceso="Coordinadores de Verificación",
                           subseccion="Acceso al Módulo",
                           next=request.args.get('next'))


@coordinadores_bp.route('/dashboard')
@validation_required_coordinador
def coordinadores_dashboard():
    opciones_modulo = [
        {
            "nombre": "Aprobación Monitoreo de Cuchillas",
            "url": url_for('coordinadores.aprobacion_monitoreo_cuchillas'),
            "icono": "fas fa-check-circle",
            "descripcion": "Revisa y aprueba los reportes de monitoreo de cuchillas."
        }
    ]
    if session.get('coordinador_role') == 'admin':
        opciones_modulo.append({
            "nombre": "Gestión de Usuarios",
            "url": url_for('coordinadores.gestion_usuarios_coordinadores'),
            "icono": "fas fa-users-cog",
            "descripcion": "Administra los usuarios autorizados para este módulo."
        })

    return render_template('coordinadores/coordinadores_dashboard.html',
                           username_coordinador=session.get('coordinador_username', 'Coordinador de Verificación'),
                           nombre_proceso="Coordinadores de Verificación",
                           subseccion="Dashboard",
                           opciones=opciones_modulo
                           )

@coordinadores_bp.route('/aprobacion_monitoreo_cuchillas')
@validation_required_coordinador
@role_required_coordinador(['coordinator', 'admin'])
def aprobacion_monitoreo_cuchillas():
    # Obtener solo los registros pendientes de aprobación usando la función de la API
    pending_records = get_pending_monitoreo_cuchillas_for_approval()

    # Los datos del coordinador ya están en la sesión gracias a los decoradores
    id_coordinador = session.get('coordinador_employee_id', 'N/A')
    nombre_coordinador = session.get('coordinador_username', 'Coordinador de Verificación')

    # ASEGÚRATE QUE EL NOMBRE DEL ARCHIVO ES .html Y COINCIDE CON EL REAL
    return render_template('coordinadores/aprobacion_monitoreo_cuchillas.html', # Asegúrate que sea .html
                           username_coordinador=nombre_coordinador,
                           nombre_proceso="Coordinadores de Verificación",
                           subseccion="Aprobación Cuchillas",
                           data=pending_records, # ¡Pasa los datos aquí!
                           id_coordinador=id_coordinador,
                           nombre_coordinador=nombre_coordinador
                           )

# Reemplaza la función completa en coordinadores.py con este código
@coordinadores_bp.route('/validar_monitoreo_cuchillas', methods=['POST'])
@validation_required_coordinador
@role_required_coordinador(['coordinator', 'admin'])
def validar_monitoreo_cuchillas():
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    current_app.logger.info("-> INICIO: Recibiendo solicitud para validar monitoreo de cuchillas.")

    try:
        data = request.get_json()
        current_app.logger.info(f"-> PASO 1: Datos JSON recibidos: {data}")
    except Exception as e:
        current_app.logger.error(f"Error al parsear JSON: {e}", exc_info=True)
        return jsonify(success=False, message="Solicitud inválida. El formato de los datos no es JSON."), 400

    if not data:
        message = 'No se recibieron datos en la solicitud.'
        current_app.logger.error(f"-> FALLO: {message}")
        return jsonify(success=False, message=message, category="danger"), 400

    item_id = data.get('id')
    cantidad_verificada_str = data.get('cantidad_verificada')
    verificacion = data.get('verificacion')
    # --- CORRECCIÓN CLAVE AQUÍ ---
    # Usar 'id_responsable_verificacion' que es lo que envía el frontend
    responsable_verificacion = data.get('responsable_verificacion')

    # *** AÑADE ESTA LÍNEA AQUÍ ***
    current_app.logger.info(f"-> LOG COOR: ID del responsable extraído del JSON: {responsable_verificacion}")

    current_app.logger.info(f"-> PASO 2: Datos extraídos: id={item_id}, cant={cantidad_verificada_str}, verif={verificacion}, resp={responsable_verificacion}")

    if not all([item_id, cantidad_verificada_str, verificacion, responsable_verificacion]):
        message = f"Datos incompletos para la validación. Datos recibidos: {data}"
        current_app.logger.error(f"-> FALLO: {message}")
        if is_ajax:
            return jsonify(success=False, message=message, category="danger"), 400
        flash(message, 'danger')
        return redirect(url_for('coordinadores.aprobacion_monitoreo_cuchillas'))

    try:
        cantidad_verificada = int(cantidad_verificada_str)
    except (ValueError, TypeError):
        message = 'La cantidad verificada debe ser un número entero válido.'
        current_app.logger.error(f"-> FALLO: Error de tipo al convertir 'cantidad_verificada': '{cantidad_verificada_str}' no es un número.")
        if is_ajax:
            return jsonify(success=False, message=message, category="danger"), 400
        flash(message, 'danger')
        return redirect(url_for('coordinadores.aprobacion_monitoreo_cuchillas'))

    result = update_monitoreo_cuchillas_record(item_id, cantidad_verificada, verificacion, responsable_verificacion)
    
    current_app.logger.info(f"-> PASO 3: Resultado de la API: {result}")

    if result['success']:
        message = 'Registro aprobado con éxito.'
        if is_ajax:
            return jsonify(success=True, message=message, category="success"), 200
        flash(message, 'success')
        return redirect(url_for('coordinadores.aprobacion_monitoreo_cuchillas'))
    else:
        message = f"Error al actualizar el registro: {result['message']}"
        current_app.logger.error(f"-> FALLO: {message}")
        if is_ajax:
            return jsonify(success=False, message=message, category="danger"), 400
        flash(message, 'danger')
        return redirect(url_for('coordinadores.aprobacion_monitoreo_cuchillas'))


@coordinadores_bp.route('/exit_module') # Ruta para salir del módulo
def coordinadores_exit_module():
    _clear_coordinador_session() # Usar la función auxiliar para limpiar
    flash('Has salido del módulo de Coordinadores.', 'info')
    # Redirige al login principal de la aplicación para una salida completa.
    return redirect(url_for('main.login'))

@coordinadores_bp.route('/gestion_usuarios')
@validation_required_coordinador
@role_required_coordinador(['admin'])
def gestion_usuarios_coordinadores():
    return render_template('coordinadores/gestion_usuarios.html',
                           username_coordinador=session.get('coordinador_username', 'Coordinador de Verificación'),
                           nombre_proceso="Coordinadores de Verificación",
                           subseccion="Gestión de Usuarios")