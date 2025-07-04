# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\impresion.py

from flask import Blueprint, render_template, session, url_for

impresion_bp = Blueprint('impresion', __name__, 
                           template_folder='../templates', 
                           static_folder='../static', 
                           url_prefix='/impresion')

@impresion_bp.route('/dashboard')
def proceso_impresion_dashboard():
    opciones = [{
        "nombre": "Formulario Ambiental", 
        "url": url_for('impresion.impresion_form_ambiental'), 
        "icono": "fas fa-seedling", 
        "descripcion": "Registrar datos ambientales del proceso de impresión."
    }, {
        "nombre": "Solicitud de Cores",
        "url": url_for('shared_forms.solicitud_cores_form', origen='impresion'), 
        "icono": "fas fa-tape", 
        "descripcion": "Solicitar cores para el proceso de Impresión."
    }]
    
    return render_template(
        'processes/impresion/impresion_dashboard.html',
        nombre_proceso="Impresión",
        username=session.get('user_name'),
        opciones=opciones
    )

@impresion_bp.route('/form_ambiental', methods=['GET', 'POST'])
def impresion_form_ambiental():
    # Aquí puedes implementar la lógica para tu formulario ambiental de impresión
    # Por ahora, solo renderiza la plantilla.
    return render_template(
        'processes/impresion/impresion_form_ambiental.html',
        nombre_proceso="Impresión",
        subseccion="Formulario Ambiental",
        username=session.get('user_name'),
        url_volver=url_for('impresion.proceso_impresion_dashboard')
    )

# Añade más rutas y lógica específica para Impresión aquí.