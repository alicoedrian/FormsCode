# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\extrusion.py

from flask import Blueprint, render_template, session, url_for

extrusion_bp = Blueprint('extrusion', __name__, 
                                 template_folder='../templates', 
                                 static_folder='../static', 
                                 url_prefix='/extrusion')

@extrusion_bp.route('/dashboard')
def proceso_extrusion_dashboard():
    opciones = [
        {"nombre": "Registro de Extrusión", "url": "#", "icono": "fas fa-industry", "descripcion": "Registrar datos de la extrusión."},
        {
            "nombre": "Solicitud de Cores",
            "url": url_for('shared_forms.solicitud_cores_form', origen='extrusion'), 
            "icono": "fas fa-tape", 
            "descripcion": "Solicitar cores para el proceso de Extrusión."
        }
    ]
    return render_template(
        'processes/extrusion/extrusion_dashboard.html',
        nombre_proceso="Extrusión",
        username=session.get('user_name'),
        opciones=opciones
    )

# Añade más rutas y lógica específica para Extrusión aquí.