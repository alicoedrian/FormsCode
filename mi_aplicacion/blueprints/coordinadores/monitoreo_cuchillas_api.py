import requests
import json
from flask import current_app
from datetime import datetime
import pytz
from urllib.parse import urlencode, urlparse, urlunparse # <-- ¡Importaciones esenciales para manipular URLs!

# Desactivar advertencias de SSL inseguro (solo para desarrollo)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_monitoreo_cuchillas_data():
    """
    Obtiene todos los registros de monitoreo de cuchillas del webhook de consulta.
    Utiliza la URL configurada en WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION.
    Retorna una lista de diccionarios con los datos o una lista vacía en caso de error.
    """
    webhook_url = current_app.config.get('WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION')
    webhook_auth_token = current_app.config.get('WEBHOOK_AUTH')

    if not webhook_url:
        current_app.logger.error("WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION no configurada.")
        return []

    headers = {}
    if webhook_auth_token:
        headers['Authorization'] = webhook_auth_token

    try:
        current_app.logger.info(f"Intentando obtener datos de monitoreo de cuchillas de: {webhook_url}")
        response = requests.get(webhook_url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()  # Lanza una excepción para errores HTTP (4xx o 5xx)
        data = response.json()
        current_app.logger.info("Datos de monitoreo de cuchillas obtenidos con éxito.")
        return data
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error al obtener datos del webhook de monitoreo de cuchillas: {e}", exc_info=True)
        return []
    except json.JSONDecodeError:
        current_app.logger.error("Error al decodificar la respuesta JSON del webhook de monitoreo de cuchillas.")
        return []
    except Exception as e:
        current_app.logger.error(f"Error inesperado en get_monitoreo_cuchillas_data: {e}", exc_info=True)
        return []

def get_pending_monitoreo_cuchillas_for_approval():
    """
    Obtiene solo los registros de monitoreo de cuchillas que están pendientes de aprobación.
    Un registro se considera pendiente si 'cantidad_verificada' y 'verificacion' son nulos.
    """
    all_records = get_monitoreo_cuchillas_data()
    pending_records = [
        item for item in all_records
        if item.get('cantidad_verificada') is None and item.get('verificacion') is None
    ]
    current_app.logger.info(f"Se encontraron {len(pending_records)} registros pendientes de aprobación.")
    return pending_records

def update_monitoreo_cuchillas_record(item_id, cantidad_verificada, verificacion, responsable_verificacion):
    """
    Actualiza un registro específico de monitoreo de cuchillas en el webhook/API.
    La URL de actualización se construye dinámicamente con el 'id_monitoreo' como parámetro de consulta.
    Retorna un diccionario con 'success' y 'message'.
    """
    # Usamos la NUEVA URL configurada para la actualización por coordinador
    base_update_url = current_app.config.get('WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION_COOR')
    webhook_auth_token = current_app.config.get('WEBHOOK_AUTH')

    if not base_update_url:
        current_app.logger.error("WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION_COOR no configurada para actualización.")
        return {"success": False, "message": "URL de actualización no configurada."}

    headers = {
        'Content-Type': 'application/json',
    }
    if webhook_auth_token:
        headers['Authorization'] = webhook_auth_token

    # --- Lógica para construir la URL dinámica con el id_monitoreo como parámetro de consulta ---
    # Parseamos la URL base para manipular sus componentes
    parsed_url = urlparse(base_update_url)
    
    # Creamos un diccionario con el parámetro id_monitoreo
    query_params_to_add = {'id_monitoreo': item_id}

    # Combinamos cualquier parámetro de consulta existente con el nuevo
    # Esto es robusto por si la URL base ya tuviera algún parámetro.
    existing_query_dict = dict(q.split('=') for q in parsed_url.query.split('&') if '=' in q) if parsed_url.query else {}
    combined_query_params = {**existing_query_dict, **query_params_to_add}

    # Codificamos los parámetros de consulta y reconstruimos la URL
    encoded_query = urlencode(combined_query_params)
    update_url_with_id = urlunparse(parsed_url._replace(query=encoded_query))
    # --- FIN Lógica para construir la URL dinámica ---

    # --- Payload con solo los 3 campos solicitados ---
    payload_to_send = {
        "cantidad_verificada": cantidad_verificada,
        "verificacion": verificacion,
        "responsable_verificacion": responsable_verificacion
    }
    
    try:
        current_app.logger.info(f"Intentando enviar actualización para registro {item_id} a: {update_url_with_id} con payload: {payload_to_send}")
        
        # Usamos POST a la URL que ahora incluye el id_monitoreo como query parameter
        response = requests.post(update_url_with_id, headers=headers, json=payload_to_send, timeout=10, verify=False)
        
        response.raise_for_status() # Lanza una excepción para códigos de estado de error HTTP

        current_app.logger.info(f"Actualización para registro {item_id} enviada con éxito. Respuesta: {response.status_code} - {response.text}")
        return {"success": True, "message": "Registro actualizado con éxito."}

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error al enviar actualización para el registro {item_id}: {e}", exc_info=True)
        return {"success": False, "message": f"Error al actualizar el registro: {e}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado en update_monitoreo_cuchillas_record para ID {item_id}: {e}", exc_info=True)
        return {"success": False, "message": f"Error interno al procesar actualización: {e}"}