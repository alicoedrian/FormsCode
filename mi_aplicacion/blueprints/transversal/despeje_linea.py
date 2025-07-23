# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\transversal\despeje_linea.py

import urllib3
from datetime import datetime
import pytz
import requests
from flask import (
    Blueprint, render_template, request, jsonify,
    session, current_app, url_for, redirect, flash
)
# Importamos las funciones de la API de Epicor, incluyendo la nueva de carnet
from ...utils.epicor_api import get_employee_name_from_id, get_job_data, get_employee_by_carnet_id 

# Desactivar advertencias de SSL inseguro (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

despeje_linea_bp = Blueprint(
    'despeje_linea', __name__,
    template_folder='../../../templates', 
    static_folder='../../../static'      
)

# APIs existentes (sin cambios, ya que ahora se usan en el frontend directamente para sus funciones)
@despeje_linea_bp.route('/api/empleado', methods=['GET'])
def api_empleado_despeje():
    eid = request.args.get('id')
    if not eid:
        return jsonify(success=False, nombre="ID no proporcionado"), 400
    res = get_employee_name_from_id(eid) # Esta función usa EPICOR_API_PAUSAS_ACTIVAS (por ID de empleado)
    if res["success"]:
        return jsonify(success=True, nombre=res["nombre"])
    return jsonify(success=False, nombre=res["message"]), 404

@despeje_linea_bp.route('/api/trabajo/<trabajo_id>', methods=['GET'])
def api_trabajo_despeje(trabajo_id):
    if not trabajo_id:
        return jsonify(success=False, error="Trabajo ID faltante"), 400
    res = get_job_data(trabajo_id) # Esta función usa EPICOR_API_TRABAJOS_FORM
    if res["success"]:
        return jsonify(res)
    return jsonify(success=False, error=res["message"]), 404

# --- NUEVA RUTA API para consultar datos del carnet del AUTORIZADOR ---
@despeje_linea_bp.route('/api/carnet/<carnet_id>', methods=['GET'])
def api_carnet_despeje(carnet_id):
    """
    Consulta la API de Epicor HMP_PausasActivas por ID de Carnet.
    Devuelve nombre y área/departamento.
    """
    if not carnet_id:
        return jsonify(success=False, error="ID de carnet no proporcionado."), 400
    
    # Usar la función de utilidad get_employee_by_carnet_id
    res = get_employee_by_carnet_id(carnet_id)
    
    if res["success"]:
        # Devolvemos éxito junto con el nombre y el área
        return jsonify(success=True, nombre=res["nombre"], area=res["area"])
    else:
        # Devolvemos el error específico de la utilidad
        return jsonify(success=False, error=res["message"]), 404 # 404 si no encontrado, 500 si error de conexión


@despeje_linea_bp.route('/despeje_linea_form', methods=['GET','POST'])
def despeje_linea_form():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    form_data = {} 
    
    proceso_origen = request.args.get('origen', 'General') 
    
    # --- Definir nombre del proceso de origen y URL de retorno para el breadcrumb ---
    proceso_origen_nombre_breadcrumb = None
    url_volver_proceso_breadcrumb = None

    # Mapeo de 'origen' a nombre legible y URL de dashboard
    if proceso_origen == 'extrusion':
        proceso_origen_nombre_breadcrumb = "Extrusión Empaques"
        url_volver_proceso_breadcrumb = url_for('extrusion.proceso_extrusion_dashboard')
    elif proceso_origen == 'impresion':
        proceso_origen_nombre_breadcrumb = "Impresión Empaques"
        url_volver_proceso_breadcrumb = url_for('impresion.proceso_impresion_dashboard')
    elif proceso_origen == 'laminacion':
        proceso_origen_nombre_breadcrumb = "Laminación"
        url_volver_proceso_breadcrumb = url_for('laminacion.proceso_laminacion_dashboard')
    elif proceso_origen == 'corte':
        proceso_origen_nombre_breadcrumb = "Corte"
        url_volver_proceso_breadcrumb = url_for('corte.proceso_corte_dashboard')
    elif proceso_origen == 'sellado':
        proceso_origen_nombre_breadcrumb = "Sellado"
        url_volver_proceso_breadcrumb = url_for('sellado.proceso_sellado_dashboard')
    # Añade más 'elif' para otros orígenes si los tienes
    
    # Fallback para el botón "Volver" si el origen no está en el mapeo o es 'General'
    # Esta 'url_volver' se usa en el botón final del formulario
    url_volver_fallback_button = url_volver_proceso_breadcrumb if url_volver_proceso_breadcrumb else url_for('main.home')


    form_data['proceso_origen'] = proceso_origen # Esto parece ser para el campo oculto o readonly del formulario

    if request.method == 'POST':
        datos = request.get_json() 
        form_data = datos.copy() 
        validation_errors = [] 

        def to_float(x):
            try:
                if x is not None and str(x).strip() != "":
                    return float(str(x).replace(',', '.'))
                return None
            except (ValueError, TypeError):
                return None

        def to_int(x):
            try:
                if x is not None and str(x).strip() != "":
                    return int(float(str(x).replace(',', '.')))
                return None
            except (ValueError, TypeError):
                return None

        # --- Validación de campos obligatorios ---
        # `autorizado_por_carnet`, `nombre_autorizado`, `cargo_autorizado` ahora son obligatorios
        required_fields = {
            'id_empleado': "ID Operario",
            'trabajo': "Trabajo",
            'parte': "Parte",
            'proceso_form': "Proceso de Origen", 
            'tipo_despeje': "Tipo de Despeje", 
            'autorizado_por_carnet': "ID Carnet Autorizador",
            'nombre_autorizado': "Nombre Autorizador", 
            'cargo_autorizado': "Cargo Autorizador" 
        }
        for f, label in required_fields.items():
            val = datos.get(f)
            if val is None or str(val).strip() == "":
                validation_errors.append((f, f'El campo "{label}" es obligatorio.'))
            
            # Validaciones de formato para IDs
            if f == 'id_empleado' and val and not str(val).isdigit():
                validation_errors.append((f, f'El campo "{label}" debe ser un número entero válido.'))
            if f == 'autorizado_por_carnet' and val and not str(val).isdigit(): 
                validation_errors.append((f, f'El campo "{label}" debe contener solo dígitos.'))


        # --- Validar ID de empleado del operario en Epicor ---
        nombre_empleado_operario = "" 
        employee_id_input = datos.get('id_empleado')
        if employee_id_input and to_int(employee_id_input) is not None: 
            emp_api_res = get_employee_name_from_id(employee_id_input)
            if not emp_api_res["success"]:
                validation_errors.append(('id_empleado',f"Error validando ID Operario: {emp_api_res['message']}"))
            else:
                nombre_empleado_operario = emp_api_res["nombre"] or ""

        # --- Validar trabajo en Epicor ---
        parte_del_trabajo_api = ""
        trabajo_input = datos.get('trabajo')
        if trabajo_input:
            job_api_res = get_job_data(trabajo_input)
            if not job_api_res["success"]:
                validation_errors.append(('trabajo',f"Error validando trabajo: {job_api_res['message']}"))
            else:
                parte_del_trabajo_api = job_api_res.get('parte', "")
                # Solo añadir advertencia si la parte del trabajo de la API es diferente a la ingresada
                # ya que el campo 'parte' en el formulario es readonly y se llena desde la API
                # Si el campo 'parte' no se llenó, es error de la API o del frontend.
                if datos.get('parte') != parte_del_trabajo_api:
                    # Esta validación puede ser menos estricta si el campo 'parte' es readonly y ya se validó
                    # que el trabajo existe. Podría ser un error de sincronización de datos o que la API no devuelva parte.
                    # Por ahora, la mantenemos como advertencia si los datos no coinciden, aunque en un readonly debería coincidir
                    validation_errors.append(('parte', f"ADVERTENCIA: La parte del trabajo '{trabajo_input}' según Epicor es '{parte_del_trabajo_api}', diferente a la ingresada ('{datos.get('parte')}')."))
        
        # --- Validación del Autorizador por Carnet ---
        nombre_autorizador = ""
        cargo_autorizador = "" # Este será el departamento/área
        carnet_autorizador_input = datos.get('autorizado_por_carnet')
        if carnet_autorizador_input and str(carnet_autorizador_input).isdigit(): # Solo si es numérico
            auth_api_res = get_employee_by_carnet_id(carnet_autorizador_input)
            if not auth_api_res["success"]:
                validation_errors.append(('autorizado_por_carnet',f"Error validando Autorizador (Carnet): {auth_api_res['message']}"))
            else:
                nombre_autorizador = auth_api_res["nombre"] or ""
                cargo_autorizador = auth_api_res["area"] or ""
                # Actualizar form_data para repoblar los campos de nombre/cargo en el frontend
                datos['nombre_autorizado'] = nombre_autorizador
                datos['cargo_autorizado'] = cargo_autorizador
        
        # --- Validación de Aspectos a Revisar (SI/NO/N/A y observaciones) ---
        aspectos_a_revisar_campos = [
            'prod_anterior_estibado', 
            'unidades_ausentes', 
            'materia_prima_ausente',
            'orden_entregada_coordinador',
            'area_limpia_ordenada',
            'nuevo_material_etiquetado',
            'documentacion_requerida'
        ]
        
        for campo_base in aspectos_a_revisar_campos:
            val_snna = datos.get(campo_base) 
            obs_campo = datos.get(f'{campo_base}_observaciones', '').strip()

            if val_snna is None or val_snna == "":
                validation_errors.append((campo_base, f'Seleccione SI/NO/N/A para "{campo_base.replace("_", " ").capitalize()}"'))
            
            elif val_snna == "NO" and not obs_campo:
                validation_errors.append((f'{campo_base}_observaciones', f'ADVERTENCIA: Considere añadir observaciones para "{campo_base.replace("_", " ").capitalize()}" cuando la respuesta es "NO".'))


        # --- Si hay errores de validación, devuelve la respuesta adecuada al frontend ---
        if validation_errors:
            # Construye el HTML de los detalles de error con saltos de línea para el frontend
            details_html = "<br>".join([msg for _,msg in validation_errors])
            
            # Determina si hay errores críticos (no advertencias)
            is_danger = any("ADVERTENCIA" not in msg for _, msg in validation_errors)
            category = "danger" if is_danger else "warning"

            return jsonify(success=False if is_danger else True, 
                           message="Errores de validación." if is_danger else "Advertencias de Formulario.",
                           details=details_html, category=category,
                           form_data=datos), 400 if is_danger else 200 

        # ——— Construir el payload JSON (después de todas las validaciones) ———
        tz = pytz.timezone(current_app.config.get('TIMEZONE','America/Bogota'))
        ts = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        
        payload = {
            "fecha": ts,
            "id_operario": datos.get('id_empleado'), 
            "nombre_operario": nombre_empleado_operario, 
            "proceso_origen": datos.get('proceso_form'), 
            "trabajo": datos.get('trabajo'),
            "parte": datos.get('parte'), 
            "tipo_despeje": datos.get('tipo_despeje'), 
            # Si "razon_despeje" y "despeje_realizado" y "confirmacion_supervisor"
            # no están en el formulario HTML, aparecerán como None aquí.
            # Asegúrate de que tu modelo de DB maneje esto, o asigna valores por defecto.
            "razon_despeje": datos.get('razon_despeje'), 
            "despeje_realizado": datos.get('despeje_realizado'), 
            "confirmacion_supervisor": datos.get('confirmacion_supervisor'), 
            "observaciones_generales": datos.get('observaciones'),

            "autorizado_por_carnet": datos.get('autorizado_por_carnet'), 
            "nombre_autorizado": datos.get('nombre_autorizado'), 
            "cargo_autorizado": datos.get('cargo_autorizado'), 

            # Aspectos a revisar (SI/NO/N/A y sus observaciones)
            "prod_anterior_estibado_snna": datos.get('prod_anterior_estibado'), 
            "prod_anterior_estibado_observaciones": datos.get('prod_anterior_estibado_observaciones'),
            "unidades_ausentes_snna": datos.get('unidades_ausentes'),
            "unidades_ausentes_observaciones": datos.get('unidades_ausentes_observaciones'),
            "materia_prima_ausente_snna": datos.get('materia_prima_ausente'),
            "materia_prima_ausente_observaciones": datos.get('materia_prima_ausente_observaciones'),
            "orden_entregada_coordinador_snna": datos.get('orden_entregada_coordinador'),
            "orden_entregada_coordinador_observaciones": datos.get('orden_entregada_coordinador_observaciones'),
            "area_limpia_ordenada_snna": datos.get('area_limpia_ordenada'),
            "area_limpia_ordenada_observaciones": datos.get('area_limpia_ordenada_observaciones'),
            "nuevo_material_etiquetado_snna": datos.get('nuevo_material_etiquetado'),
            "nuevo_material_etiquetado_observaciones": datos.get('nuevo_material_etiquetado_observaciones'),
            "documentacion_requerida_snna": datos.get('documentacion_requerida'),
            "documentacion_requerida_observaciones": datos.get('documentacion_requerida_observaciones')
        }
        
        current_app.logger.info("JSON del Payload del Formulario Despeje de Línea (Simulado):")
        current_app.logger.info(payload)

        return jsonify(success=True, message="Despeje de Línea registrado exitosamente.",
                       category="success", data=payload), 200

    # Método GET: simplemente mostrar el formulario (inicialmente vacío)
    # --- Modificar para pasar las variables del breadcrumb ---
    return render_template(
        'shared_forms/despeje_linea_form.html', 
        nombre_proceso=proceso_origen.capitalize(), # Este es el nombre del proceso actual (Sellado, Corte, etc.)
        subseccion="Despeje de Línea (FORMATO EN PRUEBA)", # Este es el nombre del formulario actual
        fecha_actual=datetime.now(pytz.timezone(current_app.config.get('TIMEZONE','America/Bogota'))).strftime('%Y-%m-%d'),
        form_data=form_data, 
        username=session.get('user_name'),
        url_volver=url_volver_fallback_button, # Para el botón de "Volver" al final del formulario
        proceso_origen=proceso_origen, # Para el campo oculto/readonly del formulario
        # --- VARIABLES CLAVE PARA EL BREADCRUMB ---
        proceso_origen_nombre=proceso_origen_nombre_breadcrumb, # Nombre legible del origen para el breadcrumb
        url_volver_proceso=url_volver_proceso_breadcrumb # URL de retorno al dashboard de origen para el breadcrumb
    )

