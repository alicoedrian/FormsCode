# mi_aplicacion/blueprints/taras/taras_api.py

import requests
import json
import logging
from flask import current_app 

logger = logging.getLogger(__name__)


# --- FUNCIÓN ÚNICA: get_solicitudes_cores ---
def get_solicitudes_cores():
    data = []
    error_message = None

    # --- OBTENER LA URL Y LA AUTENTICACIÓN DESDE app.config ---
    webhook_url_from_config = current_app.config.get('WEBHOOK_CORES_URL_SELECT')
    webhook_auth_from_config = current_app.config.get('WEBHOOK_CORES_AUTH')
    # ----------------------------------------------------------

    if not webhook_url_from_config:
        logger.error("WEBHOOK_CORES_URL_SELECT no configurada en app.config. No se puede realizar la solicitud.")
        return [], "Error: URL del webhook de solicitudes no configurada."

    if not webhook_auth_from_config:
        logger.error("WEBHOOK_CORES_AUTH no configurada en app.config. No se puede realizar la solicitud.")
        return [], "Error: Autenticación del webhook no configurada."

    try:
        headers = {
            'Authorization': webhook_auth_from_config 
        }
        # verify=False  HARDCODEADO 
        response = requests.get(webhook_url_from_config, headers=headers, timeout=10, verify=False)

        response.raise_for_status() # Lanza un error para códigos de estado HTTP 4xx/5xx

        data = response.json()
        logger.info(f"Datos recibidos del webhook en taras_api: {data}")

    except requests.exceptions.Timeout:
        error_message = 'Error al conectar con el servidor: Tiempo de espera agotado.'
        logger.error(f"Timeout al conectar con el webhook: {webhook_url_from_config}")
    except requests.exceptions.RequestException as e:
        error_message = f'Error de red o HTTP al obtener datos del webhook: {e}'
        logger.error(f"Error de solicitud al webhook {webhook_url_from_config}: {e}")
    except json.JSONDecodeError:
        error_message = 'Error al procesar la respuesta del webhook: No es un JSON válido.'
        response_text = response.text if 'response' in locals() else "No response text available."
        logger.error(f"Error de JSON al decodificar respuesta del webhook: {response_text}")
    except Exception as e:
        error_message = f'Ocurrió un error inesperado al cargar los datos: {e}'
        logger.error(f"Error inesperado en get_solicitudes_cores: {e}", exc_info=True)

    return data, error_message