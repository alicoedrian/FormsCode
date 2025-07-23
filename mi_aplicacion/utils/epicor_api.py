# d:\DocumentacionEmpaques\mi_aplicacion\utils\epicor_api.py

import requests
from flask import current_app

# Desactivar advertencias de SSL inseguro (solo para desarrollo)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Función para obtener headers de autorización ---
def get_epicor_headers():
    api_token = current_app.config.get('EPICOR_API_TOKEN')
    if not api_token:
        current_app.logger.error("EPICOR_API_TOKEN no configurado en app.config para Epicor API.")
        return None
    return {
        "Authorization": f"Basic {api_token}",
        "Content-Type": "application/json"
    }

# --- 1. Función de validación de ID de empleado (existente) ---
# Esta función usa EPICOR_API_BASE_URL (que debe ser para HMP_ValidadorID)
def validate_employee_id(employee_id):
    """
    Valida un ID de empleado contra la API de Epicor (HMP_ValidadorID) y devuelve su estado y nombre.
    Retorna un diccionario con 'success', 'message', 'user_id', 'user_name'.
    """
    base_url = current_app.config.get('EPICOR_API_BASE_URL') # URL para HMP_ValidadorID
    headers = get_epicor_headers()

    if not base_url or not headers:
        return {"success": False, "message": "Error de configuración de la API interna. Contacta a soporte."}

    api_url = f"{base_url}?ID={employee_id}"

    try:
        response = requests.get(api_url, headers=headers, timeout=5, verify=False) 

        if response.status_code == 200:
            data = response.json()
            api_value = data.get('value', [])
            if api_value and isinstance(api_value, list) and len(api_value) > 0:
                user_data = api_value[0]
                emp_status = user_data.get('EmpBasic_EmpStatus')
                emp_name = user_data.get('EmpBasic_Name', employee_id)
                emp_id = user_data.get('EmpBasic_EmpID', employee_id)

                if emp_status == 'A':
                    return {"success": True, "user_id": emp_id, "user_name": emp_name, "message": "ID válido."}
                elif emp_status in ['I', 'T']:
                    return {"success": False, "message": f"ID {employee_id} inactivo o terminado."}
                else:
                    return {"success": False, "message": f"Estado de ID ({emp_status}) no reconocido."}
            else:
                return {"success": False, "message": f"ID {employee_id} no encontrado en Epicor."}
        elif response.status_code == 401:
            current_app.logger.warning("Error 401: Token de API de Epicor inválido o expirado.")
            return {"success": False, "message": "Error de autenticación con el servicio Epicor."}
        else:
            current_app.logger.error(f"Error inesperado de la API de Epicor ({response.status_code}): {response.text}")
            return {"success": False, "message": f"Error del servicio de validación ({response.status_code})."}

    except requests.exceptions.Timeout:
        current_app.logger.warning(f"Timeout al conectar con la API de Epicor para ID {employee_id}.")
        return {"success": False, "message": "La validación de ID tardó demasiado. Intenta de nuevo."}
    except requests.exceptions.ConnectionError:
        current_app.logger.error(f"Error de conexión a la API de Epicor para ID {employee_id}.")
        return {"success": False, "message": "No se pudo conectar con el servicio de validación. Verifica tu conexión."}
    except Exception as e:
        current_app.logger.error(f"Error desconocido en validación de Epicor para ID {employee_id}: {e}", exc_info=True)
        return {"success": False, "message": "Error interno al validar ID. Contacta a soporte."}

# --- 2. Función: Obtener Nombre de Empleado por ID (para consultas AJAX del formulario) ---
# Esta función usa EPICOR_API_PAUSAS_ACTIVAS (que debe ser para HMP_PausasActivasID(ALICO)/)
def get_employee_name_from_id(employee_id):
    API_URL_EMPLOYEE_NAME = current_app.config.get("EPICOR_API_PAUSAS_ACTIVAS") # URL para HMP_PausasActivasID(ALICO)/
    headers = get_epicor_headers()

    if not API_URL_EMPLOYEE_NAME or not headers:
        current_app.logger.error("EPICOR_API_PAUSAS_ACTIVAS o headers no configurados para consulta de empleado.")
        return {"success": False, "message": "Configuración API de empleado incompleta."}

    url = f"{API_URL_EMPLOYEE_NAME}?ID={employee_id}"
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        data = response.json()
        if 'value' in data and len(data['value']) > 0:
            employee_name = data['value'][0].get("EmpBasic_Name")
            return {"success": True, "nombre": employee_name}
        else:
            return {"success": False, "message": "Empleado no encontrado."}
    except requests.RequestException as e:
        current_app.logger.error(f"Error al consultar nombre de empleado por ID {employee_id}: {e}", exc_info=True)
        return {"success": False, "message": f"Error de conexión: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener nombre de empleado: {e}", exc_info=True)
        return {"success": False, "message": "Error interno al consultar empleado."}


# --- 3. Función: Obtener Datos de Trabajo (para consultas AJAX del formulario) ---
def get_job_data(job_id):
    API_URL_JOB_DATA = current_app.config.get("EPICOR_API_TRABAJOS_FORM") # URL para HMP_TrabajosForm/
    headers = get_epicor_headers()

    if not API_URL_JOB_DATA or not headers:
        current_app.logger.error("EPICOR_API_TRABAJOS_FORM o headers no configurados para consulta de trabajo.")
        return {"success": False, "message": "Configuración API de trabajo incompleta."}

    url = f"{API_URL_JOB_DATA}?Trabajo={job_id}"
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        data = response.json()
        if "value" in data and data["value"]:
            resultado = data["value"][0]
            return {
                "success": True,
                "parte": resultado.get("JobHead_PartNum", ""),
                "cliente": resultado.get("Customer_CustID", ""),
                "estructura": resultado.get("Part_ShortChar04", ""),
                "ancho": resultado.get("Part_Number01", ""),
                "largo": resultado.get("Part_Number02", ""),
                "fuelle": resultado.get("Part_Number06", "")
            }
        else:
            return {"success": False, "message": "Trabajo no encontrado en Epicor."}
    except requests.RequestException as e:
        current_app.logger.error(f"Error al consultar datos de trabajo {job_id}: {e}", exc_info=True)
        return {"success": False, "message": f"Error de conexión: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener datos de trabajo: {e}", exc_info=True)
        return {"success": False, "message": "Error interno al consultar trabajo."}

# --- 4. NUEVA FUNCIÓN: Obtener Nombre y Departamento de Empleado por ID de Carnet ---
# Esta función usará una nueva URL: EPICOR_API_CARNET_LOOKUP (para HMP_PausasActivas)
def get_employee_by_carnet_id(carnet_id):
    API_URL_CARNET_LOOKUP = current_app.config.get("EPICOR_API_CARNET_LOOKUP") # ¡Nueva variable en .env!
    headers = get_epicor_headers()

    if not API_URL_CARNET_LOOKUP or not headers:
        current_app.logger.error("EPICOR_API_CARNET_LOOKUP o headers no configurados para consulta de carnet.")
        return {"success": False, "message": "Configuración API de carnet incompleta."}

    url = f"{API_URL_CARNET_LOOKUP}?Carnet={carnet_id}"
    try:
        response = requests.get(url, headers=headers, timeout=5, verify=False)
        response.raise_for_status()
        data = response.json()
        if 'value' in data and len(data['value']) > 0:
            user_data = data['value'][0]
            employee_name = user_data.get("EmpBasic_Name")
            employee_dept = user_data.get("EmpBasic_JCDept") # Asumiendo que este es el campo para el área/cargo
            return {"success": True, "nombre": employee_name, "area": employee_dept}
        else:
            return {"success": False, "message": "Carnet no encontrado."}
    except requests.RequestException as e:
        current_app.logger.error(f"Error al consultar carnet {carnet_id}: {e}", exc_info=True)
        return {"success": False, "message": f"Error de conexión: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al obtener datos de carnet: {e}", exc_info=True)
        return {"success": False, "message": "Error interno al consultar carnet."}