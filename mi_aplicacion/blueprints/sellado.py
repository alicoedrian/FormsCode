# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\sellado.py

from flask import Blueprint, render_template, session, url_for

sellado_bp = Blueprint('sellado', __name__, 
                                template_folder='../templates', 
                                static_folder='../static', 
                                url_prefix='/sellado')

@sellado_bp.route('/dashboard')
def proceso_sellado_dashboard():
    opciones = [
        {"nombre": "Formulario Estándares", "url": url_for('sellado.sellado_form_estandares'), "icono": "fas fa-clipboard-list", "descripcion": "Formularios de estándares de sellado."},
        {"nombre": "Formulario SE30-SE47", "url": url_for('sellado.sellado_form_SE30_SE47'), "icono": "fas fa-file-contract", "descripcion": "Formulario específico SE30-SE47."},
        {
            "nombre": "Solicitud de Cores",
            "url": url_for('shared_forms.solicitud_cores_form', origen='sellado'), 
            "icono": "fas fa-tape", 
            "descripcion": "Solicitar cores para el proceso de Sellado."
        }
    ]
    return render_template(
        'processes/sellado/sellado_dashboard.html',
        nombre_proceso="Sellado",
        username=session.get('user_name'),
        opciones=opciones
    )

@sellado_bp.route('/form_estandares', methods=['GET', 'POST'])
def sellado_form_estandares():
    # Lógica para sellado_form_estandares
    return render_template(
        'processes/sellado/sellado_form_estandares.html',
        nombre_proceso="Sellado",
        subseccion="Formulario Estándares",
        username=session.get('user_name'),
        url_volver=url_for('sellado.proceso_sellado_dashboard')
    )

@sellado_bp.route('/form_SE30_SE47', methods=['GET', 'POST'])
def sellado_form_SE30_SE47():
    # Lógica para sellado_form_SE30_SE47
    return render_template(
        'processes/sellado/sellado_form_SE30_SE47.html',
        nombre_proceso="Sellado",
        subseccion="Formulario SE30-SE47",
        username=session.get('user_name'),
        url_volver=url_for('sellado.proceso_sellado_dashboard')
    )
# Añade más rutas y lógica específica para Sellado aquí.