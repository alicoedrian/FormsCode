# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\corte.py

from flask import Blueprint, render_template, session, url_for

corte_bp = Blueprint('corte', __name__, 
                         template_folder='../templates', 
                         static_folder='../static', 
                         url_prefix='/corte')

@corte_bp.route('/dashboard')
def proceso_corte_dashboard():
    opciones = [{
        "nombre": "Registro de Corte", 
        "url": "#", # URL real de un formulario/reporte de corte
        "icono": "fas fa-file-alt", 
        "descripcion": "Registrar operaciones y mermas de corte."
    }, {
        "nombre": "Monitoreo de Refiladoras", 
        "url": "#", # URL real de un monitoreo de refiladoras
        "icono": "fas fa-cog", 
        "descripcion": "Consultar estado y producción de refiladoras."
    }, {
        "nombre": "Solicitud de Cores",
        "url": url_for('shared_forms.solicitud_cores_form', origen='corte'), 
        "icono": "fas fa-tape", 
        "descripcion": "Solicitar cores para el proceso de Corte."
    }]
    
    return render_template(
        'processes/corte/corte_dashboard.html',
        nombre_proceso="Corte",
        username=session.get('user_name'),
        opciones=opciones
    )

# Añade más rutas y lógica específica para Corte aquí.