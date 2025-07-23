# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\corte.py

from flask import Blueprint, render_template, session, url_for

corte_bp = Blueprint('corte', __name__, 
                         template_folder='../templates', 
                         static_folder='../static', 
                         url_prefix='/corte')

@corte_bp.route('/dashboard')
def proceso_corte_dashboard():
    opciones = [ {
        "nombre": "Solicitud de Cores",
        "url": url_for('shared_forms.solicitud_cores_form', origen='corte'), 
        "icono": "fas fa-tape", 
        "descripcion": "Solicitar cores para el proceso de Corte."
    },{
            "nombre": "Empalme de Turno (Checklist 5S)",
            "url": url_for('empalme_turno.empalme_turno_form', origen='corte'), 
            "icono": "fas fa-handshake", 
            "descripcion": "Registrar checklist 5S y novedades del empalme de turno."
    },{
            "nombre": "Monitoreo de Cuchillas",
            "url": url_for('monitoreo_cuchillas.monitoreo_cuchillas_form', origen='corte'), 
            "icono": "fas fa-cogs", # Opcional: puedes usar 'fas fa-cut' también si quieres
            "descripcion": "Registrar el monitoreo de las cuchillas."
        },{ 
        "nombre": "Despeje de Línea",
        "url": url_for('despeje_linea.despeje_linea_form', origen='corte'), 
        "icono": "fas fa-broom", 
        "descripcion": "Registrar el despeje de línea antes de una nueva orden."
        },
    ]
    
    return render_template(
        'processes/corte/corte_dashboard.html',
        nombre_proceso="Corte",
        username=session.get('user_name'),
        opciones=opciones
    )

# Añade más rutas y lógica específica para Corte aquí.