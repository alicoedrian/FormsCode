# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\main.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, flash, current_app
)
import requests

# --- 1. Creación del Blueprint ---
main_bp = Blueprint('main', __name__, template_folder='../templates') # Ajusta template_folder para que encuentre 'login.html' y 'home.html'

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

        api_token = current_app.config['EPICOR_API_TOKEN']
        base_url = current_app.config['EPICOR_API_BASE_URL']
        
        headers = {
            "Authorization": f"Basic {api_token}",
            "Content-Type": "application/json"
        }
        api_url = f"{base_url}?ID={employee_id}"

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
                        return redirect(next_url or url_for('main.home'))
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
            current_app.logger.warning(f"Timeout al conectar con la API de Epicor.")
            flash('El servicio de validación tardó demasiado. Intenta más tarde.', 'danger')
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error de conexión a la API de Epicor: {e}", exc_info=True)
            flash('Error de conexión al servicio de validación. Intenta más tarde.', 'danger')
        
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
        {"nombre": "Insertadoras", "url": "#", "icono": "fas fa-cogs", "descripcion": "En desarrollo.", "color_icono": "#34495E"}, # Si tienes un blueprint para Insertadoras, actualiza su URL
    ]
    return render_template('home.html', username=session.get('user_name'), procesos=procesos)


# --- 4. Ruta de Logout ---
@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('main.login'))