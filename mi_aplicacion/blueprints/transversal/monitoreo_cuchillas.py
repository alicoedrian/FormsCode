import urllib3
from datetime import datetime
import pytz
import requests
import json
from flask import (
    Blueprint, render_template, request, jsonify,
    session, current_app, url_for, redirect, flash
)
# Asegúrate de que esta ruta sea correcta para tu estructura de proyecto
from ...utils.epicor_api import get_employee_name_from_id 

# Desactivar advertencias de SSL inseguro (solo para desarrollo)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

monitoreo_cuchillas_bp = Blueprint(
    'monitoreo_cuchillas', __name__,
    template_folder='../../../templates',
    static_folder='../../../static'
)

# API para buscar empleado por ID (para el operario ID)
@monitoreo_cuchillas_bp.route('/api/empleado', methods=['GET'])
def api_empleado_cuchillas():
    eid = request.args.get('id')
    if not eid:
        return jsonify(success=False, nombre="ID no proporcionado"), 400
    res = get_employee_name_from_id(eid)
    if res["success"]:
        return jsonify(success=True, nombre=res["nombre"])
    return jsonify(success=False, nombre=res["message"]), 404


@monitoreo_cuchillas_bp.route('/monitoreo_cuchillas_form', methods=['GET','POST'])
def monitoreo_cuchillas_form():
    if 'user_id' not in session:
        flash('Por favor, inicia sesión.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    form_data = {}

    proceso_origen = request.args.get('origen', 'General')

    # --- Definir nombre del proceso de origen y URL de retorno para el breadcrumb ---
    proceso_origen_nombre_breadcrumb = None
    url_volver_proceso_breadcrumb = None

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
    
    url_volver_fallback_button = url_volver_proceso_breadcrumb if url_volver_proceso_breadcrumb else url_for('main.home')

    form_data['proceso_origen'] = proceso_origen

    if request.method == 'POST':
        datos = request.get_json()
        form_data = datos.copy()
        validation_errors = []

        def to_int(x):
            try:
                if x is not None and str(x).strip() != "":
                    return int(float(str(x).replace(',', '.')))
                return None
            except (ValueError, TypeError):
                return None

        # --- Validación de campos obligatorios ---
        PROCESOS_VALIDOS = ["Extrusion Empaques", "Impresion Empaques", "Laminacion", "Corte", "Sellado", "Insertadoras", "Aditamentos", "Procesos Manuales"]

        required_fields = {
            'proceso_seleccionado': "Proceso",
            'maquina': "Máquina",
            'id_operario': "ID Operario",
            'turno': "Turno",
            'minora_cantidad': "Minora (Cantidad)",
            'acerada_cantidad': "Acerada (Cantidad)",
        }
        for f, label in required_fields.items():
            val = datos.get(f)
            if val is None or (isinstance(val, str) and val.strip() == ""):
                if f in ['minora_cantidad', 'acerada_cantidad'] and (val == "0" or val == 0):
                    continue
                validation_errors.append((f, f'El campo "{label}" es obligatorio.'))

            if f in ['id_operario', 'id_quien_recibe'] and val:
                num_val = to_int(val)
                if num_val is None or num_val < 0:
                    validation_errors.append((f, f'El campo "{label}" debe ser un número entero no negativo.'))

            if f == 'proceso_seleccionado' and val not in PROCESOS_VALIDOS:
                validation_errors.append((f, f'El proceso seleccionado "{val}" no es válido.'))

        # --- Validar ID de operario en Epicor ---
        nombre_operario = ""
        operario_id_input = datos.get('id_operario')
        if operario_id_input and to_int(operario_id_input) is not None:
            emp_api_res = get_employee_name_from_id(operario_id_input)
            if not emp_api_res["success"]:
                validation_errors.append(('id_operario',f"Error validando ID Operario: {emp_api_res['message']}"))
            else:
                nombre_operario = emp_api_res["nombre"] or ""

        # --- Validar ID de quien recibe en Epicor ---
        nombre_quien_recibe = ""
        id_quien_recibe_input = datos.get('id_quien_recibe')
        if id_quien_recibe_input and to_int(id_quien_recibe_input) is not None:
            recibe_api_res = get_employee_name_from_id(id_quien_recibe_input)
            if not recibe_api_res["success"]:
                validation_errors.append(('id_quien_recibe', f"Error validando ID Quien Recibe: {recibe_api_res['message']}"))
            else:
                nombre_quien_recibe = recibe_api_res["nombre"] or ""

        # --- Validación de Estados de Cuchilla (al menos uno debe tener cantidad > 0) ---
        estados_cuchilla = [
            'cumple', 'oxidacion', 'perdida', 'fractura' # Nombres de keys usados en el frontend/datos
        ]

        cuchillas_registradas = False
        for k_base in estados_cuchilla:
            cantidad_str = datos.get(f'estado_cuchilla_{k_base}_cantidad')
            cantidad_int = to_int(cantidad_str)

            if cantidad_int is not None and cantidad_int > 0:
                cuchillas_registradas = True
                break

        if not cuchillas_registradas:
            validation_errors.append(('estado_cuchilla', 'Debe registrar al menos una cantidad mayor a cero para un Estado de Cuchilla (Cumple, Oxido, Perdida, Fractura).'))

        # --- Si hay errores de validación, devuelve la respuesta adecuada al frontend ---
        if validation_errors:
            details_html = "<br>".join(msg for _,msg in validation_errors)
            is_danger = any("ADVERTENCIA" not in msg for _, msg in validation_errors)
            category = "danger" if is_danger else "warning"

            return jsonify(success=False if is_danger else True,
                            message="Errores de validación." if is_danger else "Advertencias de Formulario.",
                            details=details_html, category=category,
                            form_data=datos), 400 if is_danger else 200

        # ——— Construir el payload JSON (después de todas las validaciones) ———
        tz = pytz.timezone(current_app.config.get('TIMEZONE','America/Bogota'))
        ts = datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S%z")

        payload_dict = {
            "fecha": ts,
            "proceso": datos.get('proceso_seleccionado'), 
            "maquina": datos.get('maquina'),
            "id_operario": datos.get('id_operario'),
            "nombre_operario": nombre_operario,
            "turno": datos.get('turno'),
            "minora_cantidad": to_int(datos.get('minora_cantidad')),
            "acerada_cantidad": to_int(datos.get('acerada_cantidad')),
            "estado_cuchilla_cumple_cantidad": to_int(datos.get('estado_cuchilla_cumple_cantidad')),
            "estado_cuchilla_oxidacion_cantidad": to_int(datos.get('estado_cuchilla_caso_oxidacion_cantidad')), 
            "estado_cuchilla_perdida_cantidad": to_int(datos.get('estado_cuchilla_caso_perdida_cantidad')),     
            "estado_cuchilla_fractura_cantidad": to_int(datos.get('estado_cuchilla_fractura_cantidad')),
            "id_quien_recibe": datos.get('id_quien_recibe'),
            "nombre_quien_recibe": nombre_quien_recibe,
            "observaciones": datos.get('observaciones', None),
            "cantidad_verificada": to_int(datos.get('cantidad_verificada', None)),
            "verificacion": datos.get('verificacion', None),
            "responsable_verificacion": datos.get('responsable_verificacion', None)
        }

        # --- DEBUGGING: Imprime el payload final ANTES de enviarlo ---
        current_app.logger.info(f"DEBUG: Payload final a enviar al webhook: {payload_dict}")

        # --- ENVÍO AL WEBHOOK ---
        webhook_url = current_app.config.get('WEBHOOK_MONITOREO_CUCHILLAS_URL')
        webhook_auth = current_app.config.get('WEBHOOK_AUTH') # Esto es 'Basic YWRtaW46SG0xMTkxOTI5'

        # El log de tu .env muestra que WEBHOOK_EMP_TURNO_AUTH NO tiene "Basic"
        # y WEBHOOK_AUTH SÍ lo tiene. Asegúrate de que el webhook de cuchillas
        # espera "Basic" si estás usando WEBHOOK_AUTH.
        # Si el webhook de cuchillas espera un token sin "Basic ",
        # deberías definir WEBHOOK_MONITOREO_CUCHILLAS_AUTH = "YWRtaW46SG0xMTkxOTI5" en tu .env
        # y luego usar:
        # webhook_auth_header = current_app.config.get('WEBHOOK_MONITOREO_CUCHILLAS_AUTH')
        # headers = {'Authorization': f'Basic {webhook_auth_header}'}
        # O si ya viene con Basic:
        # headers = {'Authorization': webhook_auth_header}


        if not webhook_url or not webhook_auth:
            current_app.logger.error("URL o token de autenticación del webhook de Monitoreo de Cuchillas no configurados.")
            return jsonify(success=False, message="Error de configuración del webhook. Contacta a soporte.", category="danger"), 500

        payload_json_string = json.dumps(payload_dict) 

        headers = {
            'Content-Type': 'application/json',
            'Authorization': webhook_auth # Usa el token tal como viene de config
        }

        try:
            # Primero intenta con verificación SSL (verify=True)
            # COMENTARIO: Los logs anteriores muestran que incluso con verify=False el 500 persiste.
            # Mantendremos verify=False por ahora dado el historial de problemas SSL.
            response = requests.request("POST", webhook_url, headers=headers, data=payload_json_string, timeout=5, verify=False)
            response.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
            current_app.logger.info(f"Webhook de Cuchillas enviado exitosamente. Respuesta: {response.text}")
            
            # Devolver respuesta exitosa si todo salió bien
            return jsonify(success=True, message="Monitoreo de Cuchillas registrado.",
                           category="success", data=payload_dict), 200

        except requests.exceptions.SSLError as ssl_error:
            # Este bloque se ejecutaría si verify=True estuviera activo y fallara SSL
            # Pero dado que estamos usando verify=False por defecto, es menos probable que se active.
            current_app.logger.warning(f"Error de SSL en webhook Cuchillas: {str(ssl_error)}. Reintentando sin verificación...")
            try:
                response = requests.request("POST", webhook_url, headers=headers, data=payload_json_string, timeout=5, verify=False)
                response.raise_for_status()
                current_app.logger.warning("Conexión exitosa sin verificación SSL (solo para desarrollo) para Cuchillas")
                return jsonify(success=True, message="Monitoreo de Cuchillas registrado y enviado al Webhook (con advertencia SSL).",
                               category="warning", data=payload_dict), 200
            except requests.exceptions.RequestException as e:
                current_app.logger.error(f"Error al enviar datos al webhook de Cuchillas (reintento fallido): {e}")
                return jsonify(success=False, message="Error crítico al enviar al webhook de Cuchillas.", category="danger", details=str(e)), 500
            
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error al enviar datos al webhook de Cuchillas: {e}")
            return jsonify(success=False, message="Error al enviar al webhook de Cuchillas.", category="danger", details=str(e)), 500
        except Exception as e:
            current_app.logger.error(f"Error inesperado al procesar el formulario de Cuchillas: {e}", exc_info=True)
            return jsonify(success=False, message="Ocurrió un error interno al procesar el formulario de Cuchillas.", category="danger", details='Contacte a soporte.'), 500

    # Método GET: Renderiza el formulario
    return render_template(
        'shared_forms/monitoreo_cuchillas_form.html',
        nombre_proceso=proceso_origen.capitalize(),
        subseccion="Monitoreo de Cuchilla (FORMATO EN PRUEBA)",
        fecha_actual=datetime.now(pytz.timezone(current_app.config.get('TIMEZONE','America/Bogota'))).strftime('%Y-%m-%d'),
        form_data=form_data,
        username=session.get('user_name'),
        proceso_origen_nombre=proceso_origen_nombre_breadcrumb,
        url_volver_proceso=url_volver_proceso_breadcrumb,
        url_volver=url_volver_fallback_button,
        proceso_origen=proceso_origen
    )