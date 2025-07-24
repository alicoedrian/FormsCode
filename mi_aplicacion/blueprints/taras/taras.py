# mi_aplicacion/blueprints/taras/taras.py

from flask import (
    Blueprint, render_template, request, jsonify,
    session, current_app, url_for, redirect, flash
)
from datetime import datetime
import pytz
import os
import json
from functools import wraps
# Ya no importamos requests aquí directamente, se hace en taras_api.py

# --- CAMBIO AQUÍ: Importar desde el mismo paquete (directorio) ---
from .taras_api import get_solicitudes_cores # CAmbio de '...utils.taras_api' a '.taras_api'

# Importaciones de la API de Epicor (descomenta si las necesitas y verifica la ruta)
# from ...utils.epicor_api import get_employee_name_from_id, get_job_data, get_part_data

taras_bp = Blueprint(
    'taras', __name__,
    template_folder='../../templates',
    static_folder='../../static',
    url_prefix='/taras'
)

# --- Configuración del Webhook (estas variables ya no son necesarias aquí si están en taras_api.py) ---
# WEBHOOK_URL = "https://apps.alico-sa.com/webhook-test/49f744d6-8deb-4111-b3f2-5419143c40f4"
# WEBHOOK_AUTH = "Basic YWRtaW46SG0xMTkxOTI5"

# --- Función auxiliar para limpiar la sesión del módulo de Taras ---
def _clear_taras_session():
    """Limpia todas las variables de sesión relacionadas con el módulo de Taras."""
    session.pop('taras_access_validated', None)
    session.pop('taras_role', None)
    session.pop('taras_user_id', None)
    session.pop('taras_employee_id', None)
    session.pop('taras_username', None)
    session.permanent = False

# --- Decorador para asegurar validación al entrar al módulo de Taras ---
def validation_required_taras(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('taras_access_validated'):
            flash('Debes validar tu carnet para acceder a este módulo.', 'warning')
            return redirect(url_for('taras.taras_entry', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas para el Módulo de Taras ---

@taras_bp.route('/entry', methods=['GET', 'POST'])
def taras_entry():
    if request.method == 'GET':
        if session.get('taras_access_validated'):
            _clear_taras_session()

    if request.method == 'POST':
        carnet_id = request.form.get('employee_id')
        next_url = request.form.get('next')

        if not carnet_id:
            flash('El número de carnet es requerido.', 'warning')
            return render_template('taras/taras_entry.html',
                                   nombre_proceso="Taras",
                                   subseccion="Acceso al Módulo",
                                   next=next_url)

        json_file_path = os.path.join(taras_bp.root_path, 'allowed_carnets_taras.json')

        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                allowed_carnets_data = json.load(f)

            allowed_carnets_list = allowed_carnets_data.get('allowed_carnets', [])
            carnet_str = str(carnet_id)

            if carnet_str in allowed_carnets_list:
                session['taras_access_validated'] = True
                session['taras_role'] = 'taras_user'

                session['taras_user_id'] = session.get('user_id', carnet_str)
                session['taras_username'] = session.get('user_name', 'Usuario Taras')
                session['taras_employee_id'] = carnet_str

                session.permanent = False

                return redirect(next_url or url_for('taras.solicitudes_cores_view'))
            else:
                flash('Carnet no autorizado para este módulo.', 'danger')
                _clear_taras_session()
                current_app.logger.warning(f"Intento de validación fallido para carnet: {carnet_str}. No autorizado en allowed_carnets_taras.json")

        except FileNotFoundError:
            flash('Error de configuración: El archivo de carnets autorizados para Taras no se encontró. Contacta a soporte.', 'danger')
            current_app.logger.error(f"Archivo JSON de carnets para Taras no encontrado en: {json_file_path}")
            _clear_taras_session()
        except json.JSONDecodeError:
            flash('Error de configuración: El archivo de carnets autorizados para Taras no es un JSON válido. Contacta a soporte.', 'danger')
            current_app.logger.error(f"Error al decodificar JSON en: {json_file_path}")
            _clear_taras_session()
        except Exception as e:
            flash('Ocurrió un error inesperado al validar el carnet. Intenta de nuevo o contacta a soporte.', 'danger')
            current_app.logger.error(f"Error general al validar carnet para Taras con JSON: {e}", exc_info=True)
            _clear_taras_session()

    return render_template('taras/taras_entry.html',
                           nombre_proceso="Taras",
                           subseccion="Acceso al Módulo",
                           next=request.args.get('next'))


@taras_bp.route('/solicitudes_cores')
@validation_required_taras
def solicitudes_cores_view():
    """
    Muestra el listado y la gestión de solicitudes de cores, cargando datos desde un webhook
    a través de taras_api.py.
    """
    # Llamar a la función del módulo taras_api en el mismo directorio
    solicitudes, error_message = get_solicitudes_cores()

    if error_message:
        flash(error_message, 'danger')

    return render_template(
        'taras/solicitudes_cores.html',
        nombre_proceso="Taras",
        subseccion="Gestión de Solicitudes de Cores",
        username=session.get('taras_username', 'Usuario Taras'),
        url_volver=url_for('taras.taras_entry'),
        solicitudes=solicitudes
    )

@taras_bp.route('/exit_module')
def taras_exit_module():
    _clear_taras_session()
    flash('Has salido del módulo de Taras.', 'info')
    return redirect(url_for('main.login'))