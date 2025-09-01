import urllib3
from datetime import datetime
import pytz
import requests
from flask import (
    Blueprint, render_template, request, jsonify,
    session, current_app, url_for, redirect, flash
)
from ...utils.epicor_api import get_employee_name_from_id, get_job_data

# Desactivar advertencias de SSL inseguro (solo para desarrollo, si tu webhook usa HTTPS auto-firmado)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

se35_bp = Blueprint(
    'se35', __name__,
    template_folder='../../../templates',
    static_folder='../../../static',
    url_prefix='/sellado/se35'
)

# === FUNCION PARA LA HORA DE COLOMBIA SIEMPRE ===
def get_colombia_now():
    return datetime.now(pytz.timezone('America/Bogota'))

# --- FUNCIÓN PARA ENVIAR DATOS AL WEBHOOK ---
def enviar_a_webhook_se35(datos_payload):
    """
    Envía el payload JSON al webhook configurado para SE35.
    """
    webhook_url = current_app.config.get('WEBHOOK_SE35_URL')
    webhook_token = current_app.config.get('WEBHOOK_SE35_AUTH')

    if not webhook_url or not webhook_token:
        current_app.logger.error("Webhook SE35 URL o AUTH no configurados en app.config.")
        return {"success": False, "message": "Error interno: configuración de webhook faltante."}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': webhook_token
    }

    current_app.logger.info(f"Intentando enviar a webhook: {webhook_url}")
    current_app.logger.info(f"Headers de autorización: {headers['Authorization']}")

    try:
        resp = requests.post(webhook_url, headers=headers, json=datos_payload, timeout=10, verify=True)
        resp.raise_for_status()
        current_app.logger.info(f"Webhook respondió con estado {resp.status_code}. Respuesta: {resp.text}")
        return {"success": True, "data": resp.json()}
    except requests.exceptions.SSLError as e:
        current_app.logger.warning(f"Error SSL al conectar con webhook ({e}). Reintentando sin verificación SSL.")
        try:
            resp = requests.post(webhook_url, headers=headers, json=datos_payload, timeout=10, verify=False)
            resp.raise_for_status()
            current_app.logger.info(f"Webhook conectado con éxito sin verificación SSL. Estado: {resp.status_code}. Respuesta: {resp.text}")
            return {"success": True, "data": resp.json()}
        except Exception as e:
            current_app.logger.error(f"Reintento de webhook sin verificación SSL falló: {e}", exc_info=True)
            return {"success": False, "message": f"Error al enviar datos (SSL reintento fallido): {str(e)}"}
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error de red o HTTP al enviar webhook: {e}", exc_info=True)
        if isinstance(e, requests.exceptions.HTTPError):
            return {"success": False, "message": f"Error del servidor de datos ({e.response.status_code}): {e.response.text}", "status_code": e.response.status_code}
        return {"success": False, "message": f"Error de conexión al servidor de datos: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al enviar webhook: {e}", exc_info=True)
        return {"success": False, "message": f"Error interno al procesar el envío de datos: {str(e)}"}

@se35_bp.route('/api/empleado', methods=['GET'])
def api_empleado():
    eid = request.args.get('id')
    if not eid:
        return jsonify(success=False, nombre="ID no proporcionado"), 400
    res = get_employee_name_from_id(eid)
    if res["success"]:
        return jsonify(success=True, nombre=res["nombre"])
    return jsonify(success=False, nombre=res["message"]), 404

@se35_bp.route('/api/trabajo/<trabajo_id>', methods=['GET'])
def api_trabajo(trabajo_id):
    if not trabajo_id:
        return jsonify(success=False, error="Trabajo ID faltante"), 400
    res = get_job_data(trabajo_id)
    if res["success"]:
        return jsonify(res)
    return jsonify(success=False, error=res["message"]), 404

@se35_bp.route('/', methods=['GET','POST'])
def sellado_form_se35():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    form_data = {} 

    if request.method == 'POST':
        datos = request.get_json() if request.is_json else request.form.to_dict()
        form_data = datos.copy() 
        validation_errors = [] 

        # Elimina el campo 'fecha' del POST si viene del frontend (solo referencia visual)
        if 'fecha' in datos:
            datos.pop('fecha')

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

        required_basic_fields = {
            'id_empleado': "ID Empleado", 'trabajo': "Trabajo",
            'parte': "Parte", 'cliente': "Cliente", 'estructura': "Estructura",
            'ancho': "Ancho", 'largo': "Largo", 'fuelle': "Fuelle",
            'tipo_bolsa': "Tipo de Bolsa", 'abre_boca': "Abre Boca",
            'fotocelda': "Fotocelda", 'work_mode': "Work Mode", 
            'color_sensor_fotoc': "Color Sensor Fotocelda",'doble_corte': "Doble corte", 
            'zipper': "Zipper", 'pedido_critico': "Pedido crítico"
        }
        for f, label in required_basic_fields.items():
            val = datos.get(f)
            if val is None or str(val).strip() == "":
                validation_errors.append((f, f'El campo "{label}" es obligatorio.'))

        numeric_fields_info = {
            'calibre': {'label': 'Calibre', 'type': int},
            'velocidad': {'label': 'Velocidad', 'type': int},
            'seal_set': {'label': 'Seal Set', 'type': float},
            'speed_set': {'label': 'Speed Set', 'type': float},
            'feed_rate': {'label': 'Feed Rate', 'type': float},
            'tension_adjustment': {'label': 'Tension Adjustment', 'type': int},
            'cara': {'label': 'Cara', 'type': int},
            'medida_doblecor': {'label': 'medida_doblecor', 'type': float}       
        }

        for field, info in numeric_fields_info.items():
            v = datos.get(field)
            label = info['label']
            if v is None or str(v).strip() == "":
                validation_errors.append((field, f'El campo "{label}" es obligatorio.'))
            else:
                converted_value = to_int(v) if info['type'] == int else to_float(v)
                if converted_value is None:
                    validation_errors.append((field, f'El campo "{label}" debe ser un número válido.'))
                datos[field] = converted_value 

        for i in range(1,22):
            key = f'modulo_{i}'
            v = datos.get(key)
            if v is None or str(v).strip() == "":
                validation_errors.append((key, f'Módulo {i} es obligatorio.'))
            else:
                converted_module_val = to_int(v)
                if converted_module_val is None:
                    validation_errors.append((key, f'Módulo {i} debe ser un número entero válido.'))
                datos[key] = converted_module_val 


        if datos.get('num_fotoceldas')=='otro' and (datos.get('num_fotoceldas') is None or str(datos.get('num_fotoceldas')).strip() == ""):
            validation_errors.append(('num_fotoceldas',"Especifique # de fotoceldas si elige SI en opción FOTOCELDA'."))


        nombre_empleado = "" 
        employee_id_input = datos.get('id_empleado')
        if employee_id_input and to_int(employee_id_input) is not None: 
            emp_api_res = get_employee_name_from_id(employee_id_input)
            if not emp_api_res["success"]:
                validation_errors.append(('id_empleado',f"Error validando empleado: {emp_api_res['message']}"))
            else:
                nombre_empleado = emp_api_res["nombre"] or ""

        if validation_errors:
            details_html = "<br>".join(msg for _,msg in validation_errors)
            if request.is_json:
                return jsonify(success=False, message="Errores de validación.",
                               details=details_html, category="danger",
                               form_data=datos), 400 
            flash(details_html,'danger')
            return render_template(
                'processes/sellado/sellado_form_se35.html',
                nombre_proceso="Sellado", subseccion="Formulario SE35",
                fecha_actual=get_colombia_now().strftime('%Y-%m-%d'),
                form_data=datos, 
                username=session.get('user_name'),
                url_volver=url_for('sellado.proceso_sellado_dashboard')
            ), 400


        tz = pytz.timezone(current_app.config.get('TIMEZONE','America/Bogota'))
        ts = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")
        # Siempre formatea así: 2025-07-23T11:05:00-0500

        payload = {
            "fecha": ts,
            "id_empleado": datos.get('id_empleado'),
            "nombre_empleado": nombre_empleado,
            "trabajo": datos.get('trabajo'),
            "parte": datos.get('parte'),
            "cliente": datos.get('cliente'),
            "estructura": datos.get('estructura'),
            "ancho": datos.get('ancho'),
            "largo": datos.get('largo'),
            "fuelle": datos.get('fuelle'),
            "calibre": datos.get('calibre'),
            "velocidad": datos.get('velocidad'),
            "seal_set": datos.get('seal_set'),
            "speed_set": datos.get('speed_set'),
            "feed_rate": datos.get('feed_rate'),
            "tension_adjustment": datos.get('tension_adjustment'),
            "tipo_bolsa": datos.get('tipo_bolsa'),
            "abre_boca": datos.get('abre_boca'),
            "cara": datos.get('cara'),
            "fotocelda": datos.get('fotocelda'),
            "num_fotoceldas": datos.get('num_fotoceldas') if datos.get('num_fotoceldas') == 'otro' else None,
            "desc_foto_1": datos.get('desc_foto_1') if datos.get('desc_foto_1') == 'otro' else None,
            "desc_foto_2": datos.get('desc_foto_2') if datos.get('desc_foto_2') == 'otro' else None,
            "desc_foto_3": datos.get('desc_foto_3') if datos.get('desc_foto_3') == 'otro' else None,
            "work_mode": datos.get('work_mode'),
            "color_sensor_fotoc": datos.get('color_sensor_fotoc'),
            "doble_corte": datos.get('doble_corte'),
            "medida_doblecor": datos.get('medida_doblecor'),
            "zipper": datos.get('zipper'),
            "pedido_critico": datos.get('pedido_critico'),
            "ubicacion_modulo_1": datos.get('ubicacion_modulo_1') if datos.get('ubicacion_modulo_1') == 'otro' else None,
            "ubicacion_modulo_2": datos.get('ubicacion_modulo_2') if datos.get('ubicacion_modulo_2') == 'otro' else None,
            "ubicacion_modulo_3": datos.get('ubicacion_modulo_3') if datos.get('ubicacion_modulo_3') == 'otro' else None,
            **{f"tmodulo{i}": datos.get(f"modulo_{i}") for i in range(1,23)},
            "observaciones": datos.get('observaciones')
        }
        
        current_app.logger.info("JSON del Payload del Formulario SE35 (Simulado):")
        current_app.logger.info(payload)

        # --- ENVÍO DE DATOS AL WEBHOOK ---
        webhook_result = enviar_a_webhook_se35(payload)
        
        if request.is_json:
            if webhook_result["success"]:
                return jsonify(success=True, message="Formulario enviado correctamente.",
                               category="success", data=payload), 200
            else:
                return jsonify(success=False, message=webhook_result["message"],
                               category="danger"), webhook_result.get("status_code", 500)

        flash("Formulario enviado correctamente." if webhook_result["success"] else f"Error al enviar: {webhook_result['message']}",
              "success" if webhook_result["success"] else "danger")
        return redirect(url_for('se35.sellado_form_se35'))

    # GET: Mostrar formulario vacío y fecha/hora de Bogotá en el campo
    return render_template(
        'processes/sellado/sellado_form_se35.html',
        nombre_proceso="Sellado", 
        subseccion="Formulario SE35 (FORMATO EN PRUEBA)", 
        fecha_actual=get_colombia_now().strftime('%Y-%m-%d %H:%M:%S'),
        form_data={}, 
        username=session.get('user_name'),
        url_volver=url_for('sellado.proceso_sellado_dashboard')
    )
