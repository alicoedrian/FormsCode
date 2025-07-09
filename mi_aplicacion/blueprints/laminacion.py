# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\laminacion.py

import os
import requests
import json
import urllib3 # Para desactivar la advertencia de SSL inseguro
import pytz # Para manejar zonas horarias
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, session,
    current_app, url_for, redirect, flash
)
from dotenv import load_dotenv

# Desactivar las advertencias de InsecureRequestWarning al usar verify=False.
# ¡IMPORTANT! This should only be used in development/testing environments.
# NOT in production, as it disables SSL certificate verification, which is a security risk.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Creación del Blueprint ---
laminacion_bp = Blueprint('laminacion', __name__,
                          template_folder='../templates',
                          static_folder='../static',
                          url_prefix='/laminacion')

# --- Función auxiliar para enviar datos al webhook ---
def enviar_a_webhook_externo(datos_payload):
    """Envía datos al webhook externo para la relación de mezclas con manejo de SSL."""
    webhook_url = current_app.config.get('WEBHOOK_URL') # Asumimos WEBHOOK_URL para Laminación
    webhook_auth_token = current_app.config.get('WEBHOOK_AUTH')

    if not webhook_url or not webhook_auth_token:
        current_app.logger.error("URL o token de autenticación del webhook de Mezclas no configurados en app.config.")
        return {"success": False, "message": "Error de configuración interna del webhook de Mezclas."}

    headers = {
        'Content-Type': 'application/json',
        'Authorization': webhook_auth_token # El token ya debería estar en Base64
    }
    
    try:
        # Intenta con verificación SSL, si falla, reintenta sin ella (para desarrollo)
        response = requests.post(
            webhook_url,
            headers=headers,
            json=datos_payload, # Usar 'json=' para enviar directamente un diccionario como JSON
            timeout=10, # Ajusta el timeout según sea necesario
            verify=True # Intentar con verificación SSL primero
        )
        response.raise_for_status() # Levanta excepción para 4xx/5xx

        current_app.logger.info(f"Webhook Mezclas: Respuesta SSL Ok {response.status_code} - {response.text}")
        return {"success": True, "data": response.json(), "status_code": response.status_code}

    except requests.exceptions.SSLError as ssl_err:
        current_app.logger.warning(f"SSL error con el webhook de Mezclas: {ssl_err}. Reintentando sin verificación SSL.")
        try:
            response = requests.post(
                webhook_url,
                headers=headers,
                json=datos_payload,
                timeout=10,
                verify=False # Reintentar sin verificación SSL
            )
            response.raise_for_status()
            current_app.logger.info(f"Webhook Mezclas: Respuesta verify=False Ok {response.status_code} - {response.text}")
            return {"success": True, "data": response.json(), "status_code": response.status_code}
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error en el reintento (verify=False) enviando al webhook de Mezclas: {str(e)}", exc_info=True)
            return {"success": False, "message": f"Error de conexión al sistema externo (reintento SSL): {str(e)}"}
        
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error enviando al webhook de Mezclas: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error de conexión al sistema externo: {str(e)}"}
    except json.JSONDecodeError:
        current_app.logger.error(f"El webhook de Mezclas respondió con un formato no JSON. Respuesta: {response.text if 'response' in locals() else 'N/A'}", exc_info=True)
        return {"success": False, "message": "El sistema externo respondió con un formato inesperado (no JSON)."}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al enviar a webhook de Mezclas: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error inesperado al comunicarse con el sistema externo: {str(e)}"}


@laminacion_bp.route('/dashboard')
def proceso_laminacion_dashboard():
    # Asegúrate de que el usuario esté logueado
    if 'user_id' not in session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
        return redirect(url_for('main.login', next=request.url))

    opciones = [{
        "nombre": "Relación de Mezclas",
        "url": url_for('laminacion.proceso_laminacion_form_mezclas'),
        "icono": "fas fa-flask",
        "descripcion": "Registrar nueva mezcla de adhesivos."
    }, {
        "nombre": "Solicitud de Cores",
        "url": url_for('shared_forms.solicitud_cores_form', origen='laminacion'),
        "icono": "fas fa-tape",
        "descripcion": "Solicitar cores para el proceso de Laminación."
    }, {
        "nombre": "Empalme de Turno (Checklist 5S)",
        "url": url_for('empalme_turno.empalme_turno_form', origen='laminacion'),
        "icono": "fas fa-handshake",
        "descripcion": "Registrar checklist 5S y novedades del empalme de turno."
    }]
    return render_template(
        'processes/laminacion/laminacion_dashboard.html',
        nombre_proceso="Laminación",
        username=session.get('user_name'),
        opciones=opciones
    )


@laminacion_bp.route('/relacion_mezclas', methods=['GET', 'POST'])
def proceso_laminacion_form_mezclas():
    # Asegúrate de que el usuario esté logueado
    if 'user_id' not in session:
        # Si no está logueado, redirige al login con la URL actual para volver después
        return jsonify({
            "success": False,
            "message": "Sesión expirada. Por favor, inicia sesión nuevamente.",
            "category": "danger",
            "redirect_url": url_for('main.login', next=request.url)
        }), 401 # No autorizado si la sesión ha expirado

    if request.method == 'POST':
        # Esperamos JSON de la petición AJAX
        if request.headers.get('Content-Type') == 'application/json':
            datos = request.json
        else:
            return jsonify({
                "success": False,
                "message": "Formato de solicitud incorrecto. Se esperaba JSON.",
                "category": "danger"
            }), 400

        current_app.logger.info(f"Mezclas POST recibido. Datos: {datos}")

        # === Gestión de mensajes de validación (errores críticos vs. advertencias) ===
        validation_messages = [] # Lista para almacenar diccionarios: {"level": "danger"/"warning", "text": "..."}
        
        # 1. Validaciones de campos requeridos
        campos_requeridos = [
            'maquina', 'turno', 'operario_responsable', 'referencia_adhesivo', # <-- Añadido referencia_adhesivo
            'peso_adhesivo', 'peso_correactante', 'relacion_mezcla'
        ]

        for campo in campos_requeridos:
            if not datos.get(campo):
                validation_messages.append({
                    "level": "danger",
                    "text": f'El campo "{campo.replace("_", " ").title()}" es requerido.'
                })

        # 2. Validaciones de formato numérico y división por cero
        peso_adhesivo_val = None
        peso_correactante_val = None
        relacion_mezcla_val = None

        try:
            peso_adhesivo_val = float(datos.get('peso_adhesivo'))
            peso_correactante_val = float(datos.get('peso_correactante'))
            relacion_mezcla_val = float(datos.get('relacion_mezcla'))

            if peso_correactante_val == 0:
                validation_messages.append({
                    "level": "danger",
                    "text": "El 'Peso correactante' no puede ser cero para calcular la relación."
                })
        except (ValueError, TypeError):
            validation_messages.append({
                "level": "danger",
                "text": 'Los campos "Peso adhesivo", "Peso correactante" y "Relación de mezcla" deben ser números válidos.'
            })

        # === 3. NUEVA VALIDACIÓN: Rango de la relación de mezcla (Advertencia) ===
        relacion_calculada = None # Inicializar por si hay errores que impidan el cálculo
        # Solo calcula y valida la relación si no hay errores críticos que impidan su cálculo
        if not any(msg["level"] == "danger" for msg in validation_messages):
            try:
                relacion_calculada = round(peso_adhesivo_val / peso_correactante_val, 2)
                if not (1.22 <= relacion_calculada < 1.32):
                    # Mensaje de advertencia, no bloqueante
                    validation_messages.append({
                        "level": "warning",
                        # Eliminado el ":1" del mensaje, y el rango en el texto
                        "text": f"La relación de mezcla calculada ({relacion_calculada}) no está entre los parámetros (1.22 a 1.32). Por favor, tenga cuidado."
                    })
            except ZeroDivisionError:
                # Ya manejado por la validación de peso_correactante_val == 0, así que no se agrega doble
                pass
            except Exception as e:
                current_app.logger.error(f"Error al calcular la relación de mezcla: {e}", exc_info=True)
                validation_messages.append({
                    "level": "danger",
                    "text": "Error interno al calcular la relación de mezcla."
                })
        # =======================================================================
        
        # === Evaluar los mensajes de validación para decidir la respuesta ===
        critical_errors_found = [msg for msg in validation_messages if msg["level"] == "danger"]
        warnings_found = [msg for msg in validation_messages if msg["level"] == "warning"]

        if critical_errors_found:
            # Si hay errores críticos, NO enviar al webhook, devolver error al frontend
            return jsonify({
                "success": False,
                "message": "Errores de validación.",
                "details": "<br>".join([msg["text"] for msg in critical_errors_found]),
                "category": "danger",
                "form_data": datos
            }), 400 # 400 Bad Request para errores de validación
        
        # Si NO hay errores críticos, pero sí advertencias (o ninguna de las dos), proceder al webhook
        final_message = "Registro de mezcla enviado exitosamente."
        final_category = "success"
        final_details = None

        if warnings_found:
            final_message = "Registro de mezcla enviado con advertencias."
            final_category = "warning" # Categoría para un alert amarillo en el frontend
            final_details = "<br>".join([msg["text"] for msg in warnings_found])


        # Preparar payload extendido con datos de sesión y fecha
        payload_para_webhook = {
            "maquina": datos['maquina'],
            "turno": datos['turno'],
            "operario_responsable": datos['operario_responsable'],
            "referencia_adhesivo": datos['referencia_adhesivo'], # <-- Nuevo campo en el payload
            "peso_adhesivo": peso_adhesivo_val,
            "peso_correactante": peso_correactante_val,
            "relacion_mezcla": relacion_mezcla_val, # La relación que el usuario ingresó
            "relacion_calculada_backend": relacion_calculada, # La relación calculada por el backend
            "id_empleado": session.get('user_id'),
            "id_name": session.get('user_name'),
            "marca_temporal": datetime.now(pytz.timezone(current_app.config.get('TIMEZONE', 'America/Bogota'))).strftime("%Y-%m-%d %H:%M:%S")
        }

        # Enviar a webhook (solo si no hay errores críticos)
        webhook_result = enviar_a_webhook_externo(payload_para_webhook)
        
        if webhook_result["success"]:
            return jsonify({
                "success": True,
                "message": final_message,
                "category": final_category,
                "details": final_details, # Incluye las advertencias aquí
                "data": { # Puedes incluir datos relevantes para mostrar en la notificación
                    "relacion_calculada": relacion_calculada,
                    "id_registro_webhook": webhook_result["data"].get('id')
                }
            }), 200
        else:
            # Si el webhook falló, devolver error al frontend
            current_app.logger.error(f"Fallo el envio a webhook de Mezclas: {webhook_result['message']}")
            return jsonify({
                "success": False,
                "message": "Error al registrar la mezcla.",
                "details": webhook_result["message"],
                "category": "danger"
            }), 500


    # Método GET: simplemente mostrar el formulario (inicialmente vacío)
    return render_template(
        'processes/laminacion/laminacion_form_mezclas.html',
        nombre_proceso="Laminación",
        subseccion="Relación de Mezclas",
        username=session.get('user_name'),
        url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
        form_data={} # Asegurarse de pasar form_data para la repoblación de selects en el GET
    )