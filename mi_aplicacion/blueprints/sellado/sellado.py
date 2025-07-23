# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\sellado\sellado.py

from flask import Blueprint, render_template, session, url_for, flash, redirect, request

sellado_bp = Blueprint('sellado', __name__, 
                       template_folder='../../../templates', 
                       static_folder='../../../static', 
                       url_prefix='/sellado')

@sellado_bp.route('/')
def proceso_sellado_dashboard():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('main.login', next=request.url))
        
    formularios_sellado = [

        {"nombre": "Formulario SE30/SE47", "url": url_for('se30_se47.sellado_form_se30_se47'), "icono": "fas fa-cogs", "descripcion": "Registro de parámetros de máquinas SE30 y SE47."},
        {"nombre": "Empalme de Turno (Checklist 5S)", "url": url_for('empalme_turno.empalme_turno_form', origen='sellado'), "icono": "fas fa-handshake", "descripcion": "Registrar checklist 5S y novedades del empalme de turno."},
        {"nombre": "Despeje de Línea","url": url_for('despeje_linea.despeje_linea_form', origen='sellado'), "icono": "fas fa-broom", "descripcion": "Registrar el despeje de línea antes de una nueva orden."},
        {
            "nombre": "Monitoreo de Cuchillas",
            "url": url_for('monitoreo_cuchillas.monitoreo_cuchillas_form', origen='sellado'), 
            "icono": "fas fa-cogs", # Opcional: puedes usar 'fas fa-cut' también si quieres
            "descripcion": "Registrar el monitoreo de las cuchillas."
        }
    ]
    
    return render_template(
        'processes/sellado/sellado_dashboard.html',
        nombre_proceso="Sellado",
        username=session.get('user_name'),
        opciones=formularios_sellado
    )

@sellado_bp.route('/form_estandares', methods=['GET', 'POST'])
def sellado_form_estandares():
    if 'user_id' not in session: 
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('main.login', next=request.url))
    
    return render_template(
        'processes/sellado/sellado_form_estandares.html',
        nombre_proceso="Sellado",
        subseccion="Formulario Estándares",
        username=session.get('user_name'),
        url_volver=url_for('sellado.proceso_sellado_dashboard')
    )


@sellado_bp.route('/form_se30_se47', methods=['GET', 'POST']) # <--- Esta es la URL que estás golpeando y te da error
def sellado_form_se30_se47(): # <--- Este es el nombre de la función en tu traceback (línea 71 de sellado.py)

    print("¡DEBUG!: Redirigiendo de /sellado/form_se30_se47 a /sellado/se30_se47/") # Mensaje de depuración
    return redirect(url_for('se30_se47.sellado_form_se30_se47'), code=302) # Usamos 302 para que no cachee tan fuerte la redirección