# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\empalme_turno.py

from flask import (
    Blueprint, render_template, request, redirect, url_for, session, current_app, flash, jsonify
)
from datetime import datetime
import pytz
import re
import requests # Necesitamos requests para enviar al webhook
import json     # Necesitamos json para dumps
import urllib3  # Para desactivar la advertencia de SSL inseguro

from ..utils.epicor_api import validate_employee_id # Importamos la función de validación

# Desactivar las advertencias de InsecureRequestWarning al usar verify=False.
# ¡IMPORTANTE!: Esto solo debe usarse en entornos de desarrollo/prueba.
# NO en producción, ya que deshabilita la verificación de certificados SSL, lo cual es un riesgo de seguridad.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Creación del Blueprint ---
empalme_turno_bp = Blueprint('empalme_turno', __name__,
                                template_folder='../templates',
                                static_folder='../static',
                                url_prefix='/empalme_turno')

# --- NOTA IMPORTANTE: La lista de MAQUINAS_POR_PROCESO está en empalme_turno_form.html ---


# --- Función auxiliar para enviar datos al webhook ---
def send_empalme_to_webhook(data_payload):
    webhook_url = current_app.config.get('WEBHOOK_EMP_TURNO_URL')
    webhook_auth_token = current_app.config.get('WEBHOOK_EMP_TURNO_AUTH')

    if not webhook_url or not webhook_auth_token:
        current_app.logger.error("URL o token de autenticación del webhook de Empalme de Turno no configurados.")
        return {"success": False, "message": "Error de configuración interna del webhook."}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Basic {webhook_auth_token}'
    }

    try:
        # === SOLUCIÓN TEMPORAL PARA EL ERROR SSL: verify=False ===
        response = requests.post(webhook_url, headers=headers,
                                 data=json.dumps(data_payload),
                                 timeout=15,
                                 verify=False) # <--- ¡AQUÍ ESTÁ EL CAMBIO!
        # =========================================================

        response.raise_for_status() # Levanta un HTTPError para códigos de estado 4xx/5xx (400, 500, etc.)

        current_app.logger.info(f"Webhook de Empalme de Turno: Respuesta {response.status_code} - {response.text}")

        # === Lógica CORREGIDA para interpretar la respuesta del webhook ===
        try:
            webhook_response_json = response.json()
            # Si el webhook devuelve un 'id' (indicando que el registro se creó exitosamente en la DB)
            if 'id' in webhook_response_json and webhook_response_json['id'] is not None:
                return {"success": True, "message": "Datos registrados exitosamente en la base de datos (ID: {}).".format(webhook_response_json['id'])}
            else:
                # Si la respuesta es JSON pero no contiene el 'id' esperado
                current_app.logger.error(f"Webhook respondió con JSON inesperado: {webhook_response_json}")
                return {"success": False, "message": f"Webhook no devolvió un ID de registro. Respuesta: {webhook_response_json.get('message', 'Formato inesperado')}"}
        except json.JSONDecodeError:
            # Si el webhook no devuelve JSON, pero el status code es 2xx, asumimos éxito
            if 200 <= response.status_code < 300:
                current_app.logger.warning("Webhook de Empalme de Turno: Respuesta OK, pero no es JSON.")
                return {"success": True, "message": "Datos enviados al webhook exitosamente (respuesta no JSON, pero 200 OK)."}
            else:
                # Si no es JSON y no es 2xx, es un error.
                current_app.logger.error(f"Webhook respondió con error y formato inesperado: {response.status_code} {response.text}")
                return {"success": False, "message": f"Webhook respondió con error y formato inesperado: {response.status_code} {response.text}"}

    except requests.exceptions.Timeout:
        current_app.logger.error("Timeout al enviar datos al webhook de Empalme de Turno.")
        return {"success": False, "message": "El envío al webhook tardó demasiado. Intenta de nuevo."}
    except requests.exceptions.RequestException as e: # Captura errores de conexión, DNS, etc.
        current_app.logger.error(f"Error al enviar datos al webhook de Empalme de Turno: {e}", exc_info=True)
        return {"success": False, "message": f"Error de conexión al webhook: {e}"}
    except Exception as e: # Captura cualquier otra excepción inesperada
        current_app.logger.error(f"Error inesperado en send_empalme_to_webhook: {e}", exc_info=True)
        return {"success": False, "message": "Error interno al procesar el envío al webhook."}


# --- 2. Ruta para el Formulario de Empalme de Turno (Existente) ---
@empalme_turno_bp.route('/formulario', methods=['GET', 'POST'])
def empalme_turno_form():
    user_id_session = session.get('user_id')
    user_name_session = session.get('user_name')

    if not user_id_session or not user_name_session:
        flash('Por favor, inicia sesión para acceder a este formulario.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None

    origenes_map = {
        'impresion': ('impresion.proceso_impresion_dashboard', 'Impresión'),
        'laminacion': ('laminacion.proceso_laminacion_dashboard', 'Laminación'),
        'corte': ('corte.proceso_corte_dashboard', 'Corte'),
        'extrusion': ('extrusion.proceso_extrusion_dashboard', 'Extrusión'),
        'sellado': ('sellado.proceso_sellado_dashboard', 'Sellado'),
        'insertadoras': ('main.home', 'Insertadoras')
    }

    if proceso_origen in origenes_map:
        ruta_blueprint, nombre_proceso = origenes_map[proceso_origen]
        url_volver_proceso = url_for(ruta_blueprint)
        proceso_origen_nombre = nombre_proceso
    else:
        url_volver_proceso = url_for('main.home')
        proceso_origen_nombre = "Inicio"

    if request.method == 'POST':
        datos = request.form.to_dict()

        current_app.logger.info(f"Empalme de Turno POST recibido. Datos: {datos}")

        proceso_seleccionado = datos.get('proceso_seleccionado')
        maquina_seleccionada = datos.get('maquina_seleccionada')
        turno_seleccionado = datos.get('turno')
        id_entrega_maquina = datos.get('id_entrega_maquina')

        # Checkboxes se recogen directamente si existen en 'datos' (es decir, si estaban marcados)
        seiri_elementos_inutiles = 'seiri_elementos_inutiles' in datos
        seiri_residuos_empaques = 'seiri_residuos_empaques' in datos
        seiton_insumos_organizados = 'seiton_insumos_organizados' in datos
        seiton_herramientas_ubicacion = 'seiton_herramientas_ubicacion' in datos
        seiso_limpieza_area = 'seiso_limpieza_area' in datos
        seiso_libre_polvo_residuos = 'seiso_libre_polvo_residuos' in datos
        seiso_limpio_verifico_equipos = 'seiso_limpio_verifico_equipos' in datos
        seiketsu_cumplio_rutina = 'seiketsu_cumplio_rutina' in datos
        seiketsu_reciben_materiales = 'seiketsu_reciben_materiales' in datos
        shitsuke_novedades_documentadas = 'shitsuke_novedades_documentadas' in datos
        shitsuke_empalme_verbal = 'shitsuke_empalme_verbal' in datos
        nota_adicional = datos.get('nota_adicional', '')

        errors = []
        nombre_maquina_entrega = None # Inicializar para usarla más adelante si la validación es exitosa

        # === Validaciones del lado del servidor ===
        if not proceso_seleccionado:
            errors.append('Por favor, selecciona un Proceso.')
        if not maquina_seleccionada:
            errors.append('Por favor, selecciona una Máquina.')
        if not turno_seleccionado:
            errors.append('Por favor, selecciona un Turno.')
        
        # Validar el campo ID que entregó máquina
        if not id_entrega_maquina:
            errors.append('Por favor, ingresa el ID que entregó máquina.')
        elif not re.fullmatch(r'[0-9]{1,5}', id_entrega_maquina):
            errors.append('El ID que entregó máquina debe ser numérico y tener entre 1 y 5 dígitos.')
        else:
            # Si el formato es correcto, validar contra la API de Epicor
            validation_result_id_maquina = validate_employee_id(id_entrega_maquina)
            if not validation_result_id_maquina["success"]:
                errors.append(f'ID de máquina inválido: {validation_result_id_maquina["message"]}')
            else:
                nombre_maquina_entrega = validation_result_id_maquina["user_name"]
                current_app.logger.info(f"ID {id_entrega_maquina} validado: {nombre_maquina_entrega}")

        # Obtener fecha y hora actuales (importante que ocurra después de las validaciones de campo)
        try:
            bogota_tz = pytz.timezone(current_app.config.get('TIMEZONE', 'America/Bogota'))
            now_dt_bogota = datetime.now(bogota_tz)
            fecha_hora_registro = now_dt_bogota.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            current_app.logger.error(f"Error al obtener fecha/hora: {e}", exc_info=True)
            errors.append("Error interno al registrar la fecha y hora.")

        if errors:
            for error in errors:
                flash(error, 'danger')
            # Si hay errores, repoblar el formulario con los datos enviados
            return render_template('empalme_turno/empalme_turno_form.html',
                                   username=user_name_session,
                                   proceso_origen_nombre=proceso_origen_nombre,
                                   url_volver_proceso=url_volver_proceso,
                                   form_data=datos, # Pasa todos los datos para repoblar
                                   subseccion="Checklist Empalme de Turno")

        # === Construir el payload JSON para el webhook (después de todas las validaciones) ===
        registro_empalme_payload = {
            "fecha_hora": fecha_hora_registro,
            "operario_id": user_id_session,
            "operario_nombre": user_name_session,
            "proceso_origen": proceso_origen,
            "proceso_seleccionado": proceso_seleccionado,
            "maquina_seleccionada": maquina_seleccionada,
            "id_entrega_maquina": id_entrega_maquina,
            "nombre_maquina_entrega": nombre_maquina_entrega, # Este ya tiene el nombre validado
            "turno_seleccionado": turno_seleccionado,
            "checklist_5s": {
                "seiri_elementos_inutiles": seiri_elementos_inutiles,
                "seiri_residuos_empaques": seiri_residuos_empaques,
                "seiton_insumos_organizados": seiton_insumos_organizados,
                "seiton_herramientas_ubicacion": seiton_herramientas_ubicacion,
                "seiso_limpieza_area": seiso_limpieza_area,
                "seiso_libre_polvo_residuos": seiso_libre_polvo_residuos,
                "seiso_limpio_verifico_equipos": seiso_limpio_verifico_equipos,
                "seiketsu_cumplio_rutina": seiketsu_cumplio_rutina,
                "seiketsu_reciben_materiales": seiketsu_reciben_materiales,
                "shitsuke_novedades_documentadas": shitsuke_novedades_documentadas,
                "shitsuke_empalme_verbal": shitsuke_empalme_verbal,
            },
            "nota_adicional": nota_adicional
        }
        
        current_app.logger.info(f"Payload final para Webhook: {registro_empalme_payload}")

        # === Enviar el payload al webhook ===
        webhook_send_result = send_empalme_to_webhook(registro_empalme_payload)

        if webhook_send_result["success"]:
            flash(webhook_send_result["message"], 'success') # Mostrar el mensaje de éxito del webhook
        else:
            flash(f'Error al registrar el Empalme de Turno: {webhook_send_result["message"]}', 'danger')
            current_app.logger.error(f"Fallo el envio a webhook: {webhook_send_result['message']}")


        # Redirigir a la misma URL para mostrar el mensaje flash y limpiar el formulario
        return redirect(url_for('.empalme_turno_form', origen=proceso_origen))

    # Método GET: simplemente mostrar el formulario (inicialmente vacío)
    return render_template('empalme_turno/empalme_turno_form.html',
                            username=user_name_session,
                            proceso_origen_nombre=proceso_origen_nombre,
                            url_volver_proceso=url_volver_proceso,
                            form_data={}, # Vacío para GET inicial, form_data se usará para repoblar
                            subseccion="Checklist Empalme de Turno")


# --- RUTA PARA VALIDACIÓN ASÍNCRONA DEL ID DE MÁQUINA (sin cambios) ---
@empalme_turno_bp.route('/validar_id_maquina', methods=['POST'])
def validar_id_maquina_ajax():
    employee_id = request.json.get('employee_id')

    if not employee_id:
        return jsonify({"success": False, "message": "ID de empleado no proporcionado."}), 400
    
    validation_result = validate_employee_id(employee_id)
    
    if validation_result["success"]:
        return jsonify({"success": True, "employee_name": validation_result["user_name"]}), 200
    else:
        return jsonify({"success": False, "message": validation_result["message"]}), 200