# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\main.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash, current_app
)
# Ya no necesitamos requests directamente aquí porque usamos el módulo de utilidades
# import requests 

# --- Importación de la función de validación de Epicor desde el módulo de utilidades ---
from ..utils.epicor_api import validate_employee_id # Sube un nivel (blueprints/) y entra a utils/

# --- 1. Creación del Blueprint ---
main_bp = Blueprint('main', __name__, 
                    template_folder='../templates', # Correcto: sube de 'blueprints/' a 'mi_aplicacion/templates'
                    static_folder='../static')     # Correcto: sube de 'blueprints/' a 'mi_aplicacion/static'

# --- 2. Ruta de Login (la raíz de la aplicación) ---
@main_bp.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('main.home'))

    if request.method == 'POST':
        employee_id = request.form.get('username')

        if not employee_id:
            flash('Por favor, ingresa tu ID de empleado.', 'warning')
            return redirect(url_for('main.login'))

        # --- REFACTORIZADO: Usar la función centralizada de validación de Epicor ---
        # La función validate_employee_id ya maneja la lógica de request, headers, timeout, etc.
        validation_result = validate_employee_id(employee_id) 

        if validation_result["success"]:
            session['user_id'] = validation_result['user_id']
            session['user_name'] = validation_result['user_name']
            next_url = request.form.get('next')
            return redirect(next_url or url_for('main.home'))
        else:
            flash(validation_result['message'], 'danger')
        
        return redirect(url_for('main.login', next=request.form.get('next')))

    return render_template('login.html', next=request.args.get('next'))


# --- 3. Ruta Principal del Dashboard (Home) ---
@main_bp.route('/home')
def home():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('main.login', next=request.url))
        
    procesos = [
        {"nombre": "Extrusión", "url": url_for('extrusion.proceso_extrusion_dashboard'), "icono": "fas fa-layer-group", "descripcion": "Formularios y estándares de Extrusión.", "color_icono": "#3498DB"},
        {"nombre": "Impresión", "url": url_for('impresion.proceso_impresion_dashboard'), "icono": "fas fa-print", "descripcion": "Formularios y estándares de Impresión.", "color_icono": "#9B59B6"},
        {"nombre": "Laminación", "url": url_for('laminacion.proceso_laminacion_dashboard'), "icono": "fas fa-clone", "descripcion": "Formularios y estándares.", "color_icono": "#F39C12"},
        {"nombre": "Corte", "url": url_for('corte.proceso_corte_dashboard'), "icono": "fas fa-cut", "descripcion": "Formularios y estándares de Corte.", "color_icono": "#E74C3C"},
        {"nombre": "Sellado", "url": url_for('sellado.proceso_sellado_dashboard'), "icono": "fas fa-box-open", "descripcion": "Formularios y estándares de Sellado.", "color_icono": "#2ECC71"},
        {"nombre": "Insertadoras", "url": "#", "icono": "fas fa-cogs", "descripcion": "En desarrollo.", "color_icono": "#34495E"}, 
        {"nombre": "Aditamentos", "url": "#", "icono": "fas fa-tools", "descripcion": "En desarrollo.", "color_icono": "#7F8C8D"}, 
        {"nombre": "Taras", "url": url_for('taras.taras_entry'), "icono": "fas fa-weight", "descripcion": "Módulo para la gestión de Taras de producción.", "color_icono": "#8D6E63"}, # <-- ¡CAMBIO AQUÍ!
        {"nombre": "Procesos Manuales", "url": "#", "icono": "fas fa-hand-paper", "descripcion": "En desarrollo.", "color_icono": "#AAB7B8"},
        {"nombre": "Coordinadores de Verificación", "url": url_for('coordinadores.coordinadores_entry'), "icono": "fas fa-user-tie", "descripcion": "Módulo de gestión de usuarios y verificación de datos.", "color_icono": "#3F51B5"},

    ]
    return render_template('home.html', username=session.get('user_name'), procesos=procesos)


# --- 4. Ruta de Logout ---
@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('main.login'))