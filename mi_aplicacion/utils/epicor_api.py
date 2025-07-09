# d:\DocumentacionEmpaques\mi_aplicacion\utils\epicor_api.py
import requests
from flask import current_app

def validate_employee_id(employee_id):
    """
    Valida un ID de empleado contra la API de Epicor y devuelve su estado y nombre.
    Retorna un diccionario con 'success', 'message', 'user_id', 'user_name'.
    """
    api_token = current_app.config.get('EPICOR_API_TOKEN')
    base_url = current_app.config.get('EPICOR_API_BASE_URL')

    if not api_token or not base_url:
        current_app.logger.error("EPICOR_API_TOKEN o EPICOR_API_BASE_URL no configurados en app.config.")
        return {"success": False, "message": "Error de configuración de la API interna. Contacta a soporte."}

    headers = {
        "Authorization": f"Basic {api_token}",
        "Content-Type": "application/json"
    }
    api_url = f"{base_url}?ID={employee_id}"

    try:
        response = requests.get(api_url, headers=headers, timeout=5) # Reducir timeout para validación rápida

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