# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\shared_forms.py

import os
import requests
import json 
from flask import (
    Blueprint, render_template, request, jsonify, session, 
    current_app, url_for, redirect, flash
)
from datetime import datetime
import pytz # <--- CAMBIADO: Usar pytz para consistencia con laminacion.py
# from zoneinfo import ZoneInfo # <--- ELIMINADO: Ya no se usa ZoneInfo
import urllib3

# Desactivar las advertencias de InsecureRequestWarning al usar verify=False.
# ¡IMPORTANTE!: Esto solo debe usarse en entornos de desarrollo/prueba.
# NO en producción, ya que deshabilita la verificación de certificados SSL, lo cual es un riesgo de seguridad.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- 1. Creación del Blueprint ---
shared_bp = Blueprint('shared_forms', __name__, template_folder='../templates')

# --- El código problemático de os.getenv() y RuntimeError a nivel de módulo fue eliminado previamente ---


# === FUNCIÓN AUXILIAR PARA ENVIAR AL WEBHOOK DE CORES ===
def enviar_solicitud_cores_a_webhook(datos_formulario, user_session_data):
    """Función para enviar datos de solicitud de cores al webhook externo."""
    # Acceder a las variables del webhook desde app.config
    webhook_cores_url = current_app.config.get('WEBHOOK_CORES_URL')
    webhook_cores_auth = current_app.config.get('WEBHOOK_CORES_AUTH')

    if not webhook_cores_url or not webhook_cores_auth:
        current_app.logger.error("URL o token de autenticación del webhook de Cores no configurados en app.config.")
        return {"success": False, "message": "Error de configuración interna del webhook de Cores. Contacta a soporte."}

    try:
        # Usar la marca temporal formateada directamente del user_session_data
        # que ahora viene en el formato de Laminación
        fecha_hora_solicitud = user_session_data.get('fecha_hora_registro') # <--- CAMBIADO: Nombre de la variable

        # Prepara el payload exactamente como lo espera tu webhook
        payload = {
            "marca_temporal": fecha_hora_solicitud, # <--- Usando el formato de laminacion
            "area_solicitante": datos_formulario['area_solicitante'],
            "id_solicitante": int(datos_formulario['solicitante_id']),
            "solicitante_nombre": user_session_data.get('user_name'),
            "refiladora": datos_formulario.get('refiladora', ''),
            "trabajo": datos_formulario['trabajo_ingresa'],
            "cantidad_cores": int(datos_formulario['cantidad_cores']),
            "diametro": datos_formulario['diametro'],
            "medida_mm": int(datos_formulario['medida_mm']),
            "observaciones": datos_formulario.get('observaciones', ''),
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': webhook_cores_auth
        }
        
        current_app.logger.info("Enviando solicitud de cores a webhook: %s", payload)

        try:
            response = requests.post(
                webhook_cores_url,
                headers=headers,
                json=payload,
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            current_app.logger.info("Respuesta del webhook de Cores (con SSL): %s", response.text)
            return {"success": True, "data": response.json(), "status_code": response.status_code}

        except requests.exceptions.SSLError as ssl_error:
            current_app.logger.warning(f"Error de SSL en webhook Cores: {str(ssl_error)}. Intentando sin verificación...")
            response = requests.post(
                webhook_cores_url,
                headers=headers,
                json=payload,
                timeout=5,
                verify=False
            )
            response.raise_for_status()
            current_app.logger.warning("Conexión exitosa sin verificación SSL (solo para desarrollo) para Cores")
            return {"success": True, "data": response.json(), "status_code": response.status_code}
            
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error enviando al webhook de Cores: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error de conexión al sistema externo: {str(e)}"}
    except ValueError as e:
        current_app.logger.error(f"Error en la conversión de tipos para el payload del webhook de Cores: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error en el formato de datos para el envío al webhook: {str(e)}"}
    except Exception as e:
        current_app.logger.error(f"Error inesperado al preparar/enviar webhook de Cores: {str(e)}", exc_info=True)
        return {"success": False, "message": f"Error inesperado al comunicarse con el sistema externo: {str(e)}"}


@shared_bp.route('/formulario/solicitud_cores', methods=['GET', 'POST'])
def solicitud_cores_form():
    user_id_session = session.get('user_id')
    user_name_session = session.get('user_name')

    if not user_id_session or not user_name_session:
        return jsonify({
            "success": False,
            "message": "Sesión expirada. Por favor, inicia sesión nuevamente.",
            "category": "danger",
            "redirect_url": url_for('main.login', next=request.url)
        }), 401 # Unauthorized

    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None
    
    origenes_map = {
        'impresion': ('impresion.proceso_impresion_dashboard', 'Impresión'),
        'laminacion': ('laminacion.proceso_laminacion_dashboard', 'Laminación'),
        'corte': ('corte.proceso_corte_dashboard', 'Corte'),
        'extrusion': ('extrusion.proceso_extrusion_dashboard', 'Extrusión'),
        'sellado': ('sellado.proceso_sellado_dashboard', 'Sellado'),
        'fundas': ('main.home', 'Fundas'),
    }

    if proceso_origen in origenes_map:
        ruta_blueprint, nombre_proceso = origenes_map[proceso_origen]
        url_volver_proceso = url_for(ruta_blueprint)
        proceso_origen_nombre = nombre_proceso
    else:
        url_volver_proceso = url_for('main.home')
        proceso_origen_nombre = "Inicio"

    if request.method == 'POST':
        datos = request.get_json(silent=True)
        
        if not datos:
            return jsonify({
                "success": False,
                "message": "Formato de solicitud incorrecto. Se esperaba JSON.",
                "category": "danger"
            }), 400

        current_app.logger.info(f"Solicitud de Cores POST recibida. Datos: {datos}")

        # 1. Recoger datos
        area_solicitante = datos.get('area_solicitante')
        solicitante_id = datos.get('solicitante_id')
        refiladora = datos.get('refiladora')
        trabajo_ingresa = datos.get('trabajo_ingresa')
        cantidad_cores_str = datos.get('cantidad_cores')
        diametro = datos.get('diametro')
        medida_mm_str = datos.get('medida_mm')
        observaciones = datos.get('observaciones', '')

        # 2. Validaciones
        errors = []

        if not area_solicitante:
            errors.append('Por favor, selecciona el Área que solicita.')
        if not solicitante_id or not solicitante_id.isdigit() or len(solicitante_id) != 5:
            errors.append('El ID de quien solicita debe ser un número de 5 dígitos.')
        
        if not trabajo_ingresa:
             errors.append('El campo "Trabajo Ingresa" es obligatorio.')
        elif not (1 <= len(trabajo_ingresa) <= 9):
            errors.append('El campo "Trabajo Ingresa" debe tener entre 1 y 9 caracteres.')

        if area_solicitante == 'Corte' and not refiladora:
            errors.append('Para el área de Corte, debes seleccionar una Refiladora.')
        
        try:
            cantidad_cores = int(cantidad_cores_str)
            if cantidad_cores <= 0:
                errors.append('La cantidad de cores debe ser un número positivo.')
        except (ValueError, TypeError):
            errors.append('La cantidad de cores debe ser un número entero válido.')
        
        if not diametro:
            errors.append('Por favor, selecciona un Diámetro.')
        
        try:
            medida_mm = int(medida_mm_str)
            if medida_mm <= 0:
                errors.append('La Medida (mm) debe ser un número entero positivo.')
        except (ValueError, TypeError):
            errors.append('La Medida (mm) debe ser un número entero válido.')

        if errors:
            return jsonify({
                'success': False,
                'message': 'Validación fallida',
                'category': 'danger',
                'details': '<br>'.join(errors)
            }), 400

        try:
            bogota_tz = pytz.timezone(current_app.config.get('TIMEZONE', 'America/Bogota'))
            now_dt_bogota = datetime.now(bogota_tz)
            # Formato YYYY-MM-DD HH:MM:SS para consistencia con Laminación
            fecha_hora_registro_str = now_dt_bogota.strftime("%Y-%m-%d %H:%M:%S") # <--- CAMBIADO: Formato de fecha

            user_session_data = {
                'user_id': user_id_session,
                'user_name': user_name_session,
                'fecha_hora_registro': fecha_hora_registro_str # <--- CAMBIADO: Nombre de la variable
            }
            
            webhook_response = enviar_solicitud_cores_a_webhook(datos, user_session_data)
            
            current_app.logger.info(f"Respuesta del webhook de Cores: {webhook_response}")
            
            if webhook_response.get('success'):
                return jsonify({
                    'success': True,
                    'message': webhook_response.get('message', '¡Solicitud de Cores enviada exitosamente!'),
                    'category': 'success',
                    'id_registro': webhook_response.get('id')
                }), 200
            else:
                current_app.logger.error(f"Fallo el envio a webhook de Cores: {webhook_response.get('message')}")
                return jsonify({
                    'success': False,
                    'message': 'Error al enviar la solicitud de Cores.',
                    'category': 'danger',
                    'details': webhook_response.get('message', 'Error desconocido del webhook.')
                }), 500

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error de conexión al webhook de Cores: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Error al conectar con el sistema externo de cores.',
                'category': 'danger',
                'details': str(e)
            }), 502
        
        except Exception as e:
            current_app.logger.error(f"Error inesperado en el procesamiento de cores: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'message': 'Ocurrió un error interno al procesar la solicitud de cores.',
                'category': 'danger',
                'details': 'Contacte a soporte.'
            }), 500

    # Método GET
    return render_template('shared_forms/solicitud_cores_form.html',
                            username=user_name_session,
                            proceso_origen_nombre=proceso_origen_nombre,
                            url_volver_proceso=url_volver_proceso,
                            area_solicitante_val=request.args.get('area_solicitante') or (proceso_origen if proceso_origen in ['Extrusion Empaques', 'Impresion Empaques', 'Laminacion', 'Corte', 'Fundas'] else ''),
                            solicitante_id_val=user_id_session,
                            trabajo_ingresa_val=request.args.get('trabajo_ingresa'),
                            cantidad_cores_val=request.args.get('cantidad_cores'),
                            diametro_val=request.args.get('diametro'),
                            medida_mm_val=request.args.get('medida_mm'),
                            observaciones_val=request.args.get('observaciones'),
                            refiladora_val=request.args.get('refiladora'),
                            subseccion="Solicitud de Cores")


@shared_bp.route('/sheet/monitoreo_cores')
def monitoreo_cores_sheet():
    user_name_session = session.get('user_name')
    if not user_name_session:
        flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
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
    }

    if proceso_origen in origenes_map:
        ruta_blueprint, nombre_proceso = origenes_map[proceso_origen]
        url_volver_proceso = url_for(ruta_blueprint)
        proceso_origen_nombre = nombre_proceso
    else:
        url_volver_proceso = url_for('main.home')
        proceso_origen_nombre = "Inicio"

    sheet = current_app.config.get('SHEET_SOLICITUD_CORES')
    all_records = []
    headers = []

    if sheet is None:
        return render_template('shared_forms/monitoreo_cores.html',
                               username=user_name_session,
                               url_volver_proceso=url_volver_proceso,
                               proceso_origen_nombre=proceso_origen_nombre,
                               subseccion="Monitoreo de Estado de Core",
                               records=all_records,
                               headers=headers,
                               error_message='No se pudo establecer conexión con la hoja de Google Sheets para el monitoreo. Contacta a soporte.')
    else:
        try:
            all_values = sheet.get_all_values()
            if all_values:
                headers = all_values[0][:19]
                records_raw = all_values[1:]
                records_raw.reverse() 
                
                for row in records_raw:
                    row_padded = row[:19] + [''] * (19 - len(row))
                    all_records.append(row_padded)
            else:
                return render_template('shared_forms/monitoreo_cores.html',
                                       username=user_name_session,
                                       url_volver_proceso=url_volver_proceso,
                                       proceso_origen_nombre=proceso_origen_nombre,
                                       subseccion="Monitoreo de Estado de Core",
                                       records=all_records,
                                       headers=headers,
                                       info_message='La hoja de cálculo de monitoreo está vacía.')
        except Exception as e:
            current_app.logger.error(f"Error al leer datos de la hoja de monitoreo de cores: {e}", exc_info=True)
            return render_template('shared_forms/monitoreo_cores.html',
                                   username=user_name_session,
                                   url_volver_proceso=url_volver_proceso,
                                   proceso_origen_nombre=proceso_origen_nombre,
                                   subseccion="Monitoreo de Estado de Core",
                                   records=all_records,
                                   headers=headers,
                                   error_message='Error al cargar los datos del monitoreo. Por favor, intenta más tarde.')

    return render_template('shared_forms/monitoreo_cores.html',
                           username=user_name_session,
                           url_volver_proceso=url_volver_proceso,
                           proceso_origen_nombre=proceso_origen_nombre,
                           subseccion="Monitoreo de Estado de Core",
                           records=all_records,
                           headers=headers)