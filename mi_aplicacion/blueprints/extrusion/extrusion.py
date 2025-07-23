# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\extrusion\extrusion.py

from flask import Blueprint, render_template, session, url_for, flash, redirect, request # Importar flash, redirect, request para manejo de sesión

extrusion_bp = Blueprint('extrusion', __name__, 
                                     template_folder='../../../templates', # Corregida la ruta de templates para la estructura de tu proyecto
                                     static_folder='../../../static',     # Corregida la ruta de static para la estructura de tu proyecto
                                     url_prefix='/extrusion')

@extrusion_bp.route('/dashboard')
def proceso_extrusion_dashboard():
    # Asegúrate de que el usuario esté logueado para acceder al dashboard
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('main.login', next=request.url)) # Redirige al login si no hay sesión
        
    opciones = [
        {
            "nombre": "Solicitud de Cores",
            "url": url_for('shared_forms.solicitud_cores_form', origen='extrusion'), 
            "icono": "fas fa-tape", 
            "descripcion": "Solicitar cores para el proceso de Extrusión."
        },
        {
            "nombre": "Empalme de Turno (Checklist 5S)",
            "url": url_for('empalme_turno.empalme_turno_form', origen='extrusion'), 
            "icono": "fas fa-handshake", 
            "descripcion": "Registrar checklist 5S y novedades del empalme de turno."
        },
        { 
            "nombre": "Despeje de Línea",
            "url": url_for('despeje_linea.despeje_linea_form', origen='extrusion'), 
            "icono": "fas fa-broom", 
            "descripcion": "Registrar el despeje de línea antes de una nueva orden."
        }
    ]
    return render_template(
        'processes/extrusion/extrusion_dashboard.html',
        nombre_proceso="Extrusión",
        username=session.get('user_name'),
        opciones=opciones
    )

# Añade más rutas y lógica específica para Extrusión aquí.