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

se50_bp = Blueprint(
    'se50', __name__,
    template_folder='../../../templates',
    static_folder='../../../static',
    url_prefix='/sellado/se50'
)

# === FUNCION PARA LA HORA DE COLOMBIA SIEMPRE ===
def get_colombia_now():
    return datetime.now(pytz.timezone('America/Bogota'))

# --- FUNCIÓN PARA ENVIAR DATOS AL WEBHOOK ---
def enviar_a_webhook_se50(datos_payload):
    """
    Envía el payload JSON al webhook configurado para SE50.
    """
    webhook_url = current_app.config.get('WEBHOOK_SE50')
    webhook_token = current_app.config.get('WEBHOOK_AUTH')

    if not webhook_url or not webhook_token:
        current_app.logger.error("Webhook SE50 URL o AUTH no configurados en app.config.")
        return {"success": False, "message": "Error interno: configuración de webhook faltante."}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': webhook_token
    }

    current_app.logger.info(f"Intentando enviar a webhook: {webhook_url}")
    current_app.logger.info(f"Headers de autorización: {headers['Authorization']}")

    try:
        current_app.logger.info(f"Payload a enviar al webhook: {datos_payload}")
        resp = requests.post(webhook_url, headers=headers, json=datos_payload, timeout=10, verify=True)
        resp.raise_for_status()
        current_app.logger.info(f"Webhook respondió con estado {resp.status_code}. Respuesta: {resp.text}")
        current_app.logger.info(f"Respuesta completa del webhook: {resp.text}")
        current_app.logger.info(f"JSON interpretado desde el webhook: {resp.json()}")

        return {"success": True, "data": resp.json()}
        print("Respuesta completa:", resp.text)
    except requests.exceptions.SSLError as e:
        current_app.logger.warning(f"Error SSL al conectar con webhook ({e}). Reintentando sin verificación SSL.")
        try:
            resp = requests.post(webhook_url, headers=headers, json=datos_payload, timeout=10, verify=False)
            # Loguea SIEMPRE la respuesta del servidor
            current_app.logger.error(f"Webhook (verify=False) respondió {resp.status_code}: {resp.text}")

            if resp.status_code >= 400:
                # Devuélvelo al caller para que lo veas en el flash/json
                return {
                    "success": False,
                    "message": f"Error del servidor de datos ({resp.status_code}): {resp.text}",
                    "status_code": resp.status_code,
                }

            # Si es 2xx intenta parsear JSON, si no es JSON devuelve texto crudo
            try:
                data = resp.json()
            except ValueError:
                data = {"raw": resp.text}
            return {"success": True, "data": data}

        except requests.exceptions.RequestException as e2:
            # Aquí también intenta mostrar detalle si viene con response
            status = getattr(getattr(e2, "response", None), "status_code", None)
            body = getattr(getattr(e2, "response", None), "text", str(e2))
            current_app.logger.error(f"Reintento de webhook sin verificación SSL falló: {body}", exc_info=True)
            return {
                "success": False,
                "message": f"Error al enviar datos (SSL reintento fallido): {body}",
                "status_code": status or 500,
            }

@se50_bp.route('/api/empleado', methods=['GET'])
def api_empleado():
    eid = request.args.get('id')
    if not eid:
        return jsonify(success=False, nombre="ID no proporcionado"), 400
    res = get_employee_name_from_id(eid)
    if res["success"]:
        return jsonify(success=True, nombre=res["nombre"])
    return jsonify(success=False, nombre=res["message"]), 404

@se50_bp.route('/api/trabajo/<trabajo_id>', methods=['GET'])
def api_trabajo(trabajo_id):
    if not trabajo_id:
        return jsonify(success=False, error="Trabajo ID faltante"), 400
    res = get_job_data(trabajo_id)
    if res["success"]:
        return jsonify(res)
    return jsonify(success=False, error=res["message"]), 404

@se50_bp.route('/', methods=['GET','POST'])
def sellado_form_se50():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    form_data = {} 

    if request.method == 'POST':
        datos = request.get_json() if request.is_json else request.form.to_dict()
        form_data = datos.copy() 
        validation_errors = [] 

        # Elimina el campo 'fecha' del POST si viene del frontend (solo referencia visual)
        if 'Fecha' in datos:
            datos.pop('Fecha')

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
            'ajuste_longitud': "Ajuste longitud",'tiempo_avance': "Tiempo avance", 
            'tiempo_sello': "Tiempo sello",'tiempo_estabilizacion': "Tiempo estabilizacion", 
            'velocidad_teorica': "Velocidad teorica",'velocidad_real': "Velocidad real", 
            'tiempo_perforacion': "Tiempo perforacion", 'longitud_secundaria': "Longitud secundaria",
            'marca_3': "Marca 3", 'compens_avance': "Compens avance", 'ajuste_velocidad':"Ajuste velocidad",
            'ciclo_avance': "Ciclo avance", 'modo_trabajo': "Modo Trabajo", 'modo_saltar': "Modo saltar",
            'modo_perforacion': "Modo perforacion", 'modo_pouch': "Modo Pouch", 
        }
        for f, label in required_basic_fields.items():
            val = datos.get(f)
            if val is None or str(val).strip() == "":
                validation_errors.append((f, f'El campo "{label}" es obligatorio.'))

        numeric_fields_info = {
            'balancin_1': {'label': 'Balancin 1', 'type': float},
            'balancin_2': {'label': 'Balancin 2', 'type': float},
            'balancin_3_doypack': {'label': 'Balancin 3 Doy Pack', 'type': float},
            'freno_rodillo': {'label': 'Freno rodillo', 'type': float},
            'sellador_valvulas_preselle_superior_1': {'label': 'Sellador valvulas preselle superior_1', 'type': float},
            'sellador_valvulas_preselle_inferior_2': {'label': 'Sellador valvulas preselle superior_2', 'type': float},
            'sellador_transversal_superior_9': {'label': 'Sellador transversal superior 9', 'type': float},
            'sellador_transversal_inferior_10': {'label': 'Sellador transversal superior 10', 'type': float},  
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
                'processes/sellado/sellado_form_se50.html',
                nombre_proceso="Sellado", subseccion="Formulario SE50",
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
            "ajuste_longitud": datos.get('ajuste_longitud'),
            "tiempo_avance": datos.get('tiempo_avance'),
            "tiempo_sello": datos.get('tiempo_sello'),
            "tiempo_estabilizacion": datos.get('tiempo_estabilizacion'),
            "velocidad_teorica": datos.get('velocidad_teorica'),
            "velocidad_real": datos.get('velocidad_real'),
            "tiempo_perforacion": datos.get('tiempo_perforacion'),
            "longitud_secundaria": datos.get('longitud_secundaria'),
            "marca_3": datos.get('marca_3'),
            "compens_avance": datos.get('compens_avance'),
            "ajuste_velocidad": datos.get('ajuste_velocidad'),
            "ciclo_avance": datos.get('ciclo_avance'),
            "modo_trabajo": datos.get('modo_trabajo'),
            "modo_saltar": datos.get('modo_saltar'),
            "modo_perforacion": datos.get('modo_perforacion'),
            "modo_pouch": datos.get('modo_pouch'),
            "balancin_3_doypack": datos.get('balancin_3_doypack'),
            "freno_rodillo": datos.get('freno_rodillo')  
        }

         # --- RODILLOS (coinciden con las columnas de la DB) ---
        for i in range(1, 5):
            for lado in ("der", "izq"):
                k = f"rodillo_servo{i}_{lado}"
                payload[k] = datos.get(k)  # ya validado y convertido arriba

        # --- TEMPERATURAS (exactamente como en la DB) ---
        # Válvulas preselle
        for k in (
            "sellador_valvulas_preselle_superior_1",
            "sellador_valvulas_preselle_inferior_2",
        ):
            payload[k] = datos.get(k)

        # Transversales
        for i in range(9, 17, 2):   # 9, 11, 13, 15
            payload[f"sellador_transversal_superior_{i}"] = datos.get(f"sellador_transversal_superior_{i}")
        for i in range(10, 18, 2):  # 10, 12, 14, 16
            payload[f"sellador_transversal_inferior_{i}"] = datos.get(f"sellador_transversal_inferior_{i}")

        # Longitudinales
        for i in range(17, 23, 2):  # 17, 19, 21
            payload[f"sellador_longitudinal_superior_{i}"] = datos.get(f"sellador_longitudinal_superior_{i}")
        for i in range(18, 24, 2):  # 18, 20, 22
            payload[f"sellador_longitudinal_inferior_{i}"] = datos.get(f"sellador_longitudinal_inferior_{i}")
            

        current_app.logger.info("JSON del Payload del Formulario SE50 (Simulado):")
        current_app.logger.info(payload)
        # --- ENVÍO DE DATOS AL WEBHOOK ---
        webhook_result = enviar_a_webhook_se50(payload)
        
        
        if request.is_json:
            print("Webhook result:", webhook_result)  # Depuración
            print("Payload enviado:", payload)        # Depuración
            
            if webhook_result["success"]:
                return jsonify(success=True, message="Formulario enviado correctamente.",
                            category="success", data=payload), 200
            else:
                return jsonify(success=False, message=webhook_result["message"],
                            category="danger"), webhook_result.get("status_code", 500)

        # Para el flujo normal (no JSON)
        print("Flujo normal - Webhook result:", webhook_result)
        print("Flujo normal - Payload enviado:", payload)

        flash(
            "Formulario enviado correctamente." if webhook_result["success"]
            else f"Error al enviar: {webhook_result['message']}",
            "success" if webhook_result["success"] else "danger"
        )
        return redirect(url_for('se50.sellado_form_se50'))

    # GET: Mostrar formulario vacío y fecha/hora de Bogotá en el campo
    return render_template(
        'processes/sellado/sellado_form_se50.html',
        nombre_proceso="Sellado", 
        subseccion="Formulario SE50 (FORMATO EN PRUEBA)", 
        fecha_actual=get_colombia_now().strftime('%Y-%m-%d %H:%M:%S'),
        form_data={}, 
        username=session.get('user_name'),
        url_volver=url_for('sellado.proceso_sellado_dashboard')
    )


