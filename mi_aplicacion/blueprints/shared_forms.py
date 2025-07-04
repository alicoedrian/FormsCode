# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\shared_forms.py

import os
import requests
import json 
from flask import (
    Blueprint, render_template, request, jsonify, session, 
    current_app, url_for, redirect # Se mantiene redirect para login, pero no para POST del form
)
from datetime import datetime
import pytz

# --- 1. Creación del Blueprint ---
shared_bp = Blueprint('shared_forms', __name__, template_folder='../templates')

# --- Configuración del webhook externo para Cores desde variables de entorno ---
WEBHOOK_CORES_URL = os.getenv('WEBHOOK_CORES_URL')
WEBHOOK_CORES_AUTH = os.getenv('WEBHOOK_CORES_AUTH')

# Verificar que las variables requeridas estén configuradas
if not WEBHOOK_CORES_URL or not WEBHOOK_CORES_AUTH:
    # Esto levantará un error al iniciar la app si faltan las vars
    raise RuntimeError("Faltan variables de entorno requeridas para el webhook de Cores. Asegúrate de configurar WEBHOOK_CORES_URL y WEBHOOK_CORES_AUTH en .env")

# === FUNCIÓN AUXILIAR PARA ENVIAR AL WEBHOOK DE CORES ===
def enviar_solicitud_cores_a_webhook(datos_formulario, user_session_data):
    """Función para enviar datos de solicitud de cores al webhook externo."""
    try:
        fecha_hora_solicitud = user_session_data.get('timestamp_iso')
        
        # Prepara el payload exactamente como lo espera tu webhook
        payload = {
            "fecha_hora_solicitud": fecha_hora_solicitud,
            "area_solicitante": datos_formulario['area_solicitante'],
            "id_solicitante": int(datos_formulario['solicitante_id']),
            "solicitante_nombre": user_session_data.get('user_name'),
            "refiladora": datos_formulario.get('refiladora', 'N/A'),
            "trabajo": datos_formulario['trabajo_ingresa'],
            "cantidad_cores": int(datos_formulario['cantidad_cores']),
            "diametro": datos_formulario['diametro'],
            "medida_mm": int(datos_formulario['medida_mm']),
            "observaciones": datos_formulario.get('observaciones', ''),

        }
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': WEBHOOK_CORES_AUTH
        }
        
        current_app.logger.info("Enviando solicitud de cores a webhook: %s", payload)

        # Intento con verificación SSL primero
        try:
            response = requests.post(
                WEBHOOK_CORES_URL,
                headers=headers,
                json=payload,
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            current_app.logger.info("Respuesta del webhook de Cores (con SSL): %s", response.text)
            return response.json()

        except requests.exceptions.SSLError as ssl_error:
            current_app.logger.warning(f"Error de SSL en webhook Cores: {str(ssl_error)}. Intentando sin verificación...")
            response = requests.post(
                WEBHOOK_CORES_URL,
                headers=headers,
                json=payload,
                timeout=5,
                verify=False
            )
            response.raise_for_status()
            current_app.logger.warning("Conexión exitosa sin verificación SSL (solo para desarrollo) para Cores")
            return response.json()
            
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error enviando al webhook de Cores: {str(e)}", exc_info=True)
        raise
    except ValueError as e:
        current_app.logger.error(f"Error en la conversión de tipos para el payload del webhook de Cores: {str(e)}", exc_info=True)
        raise
    except Exception as e:
        current_app.logger.error(f"Error inesperado al preparar/enviar webhook de Cores: {str(e)}", exc_info=True)
        raise

# --- 2. Ruta para el Formulario de Solicitud de Cores ---
@shared_bp.route('/formulario/solicitud_cores', methods=['GET', 'POST'])
def solicitud_cores_form():
    user_id_session = session.get('user_id')
    user_name_session = session.get('user_name')

    if not user_id_session or not user_name_session:
        return redirect(url_for('main.login', next=request.url))

    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None
    
    origenes_map = {
        'impresion': ('impresion.proceso_impresion_dashboard', 'Impresión'),
        'laminacion': ('laminacion.proceso_laminacion_dashboard', 'Laminación'),
        'corte': ('corte.proceso_corte_dashboard', 'Corte'),
        'extrusion': ('extrusion.proceso_extrusion_dashboard', 'Extrusión'),
        'sellado': ('sellado.proceso_sellado_dashboard', 'Sellado'), # Añadido sellado
        'fundas': ('main.home', 'Fundas'), # Ejemplo si Fundas no tiene dashboard propio
    }

    if proceso_origen in origenes_map:
        ruta_blueprint, nombre_proceso = origenes_map[proceso_origen]
        url_volver_proceso = url_for(ruta_blueprint)
        proceso_origen_nombre = nombre_proceso
    else:
        url_volver_proceso = url_for('main.home')
        proceso_origen_nombre = "Inicio"

    # --- Lógica POST (para envío AJAX) ---
    if request.method == 'POST':
        datos = request.get_json(silent=True) or request.form.to_dict()
        
        current_app.logger.info(f"Solicitud de Cores POST recibida. Content-Type: {request.content_type}. Datos: {datos}")

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
        if not trabajo_ingresa or not (1 <= len(trabajo_ingresa) <= 9):
            errors.append('El campo "Trabajo Ingresa" es obligatorio y debe tener entre 1 y 9 caracteres.')

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
                'errors': errors
            }), 400

        try:
            bogota_tz = pytz.timezone(current_app.config.get('TIMEZONE', 'America/Bogota'))
            now_dt_bogota = datetime.now(bogota_tz)
            fecha_hora_para_webhook_iso = now_dt_bogota.isoformat() 

            user_session_data = {
                'user_id': user_id_session,
                'user_name': user_name_session,
                'timestamp_iso': fecha_hora_para_webhook_iso
            }
            
            webhook_response = enviar_solicitud_cores_a_webhook(datos, user_session_data)
            
            current_app.logger.info(f"Respuesta del webhook de Cores: {webhook_response}")
            
            return jsonify({
                'success': True,
                'message': '¡Solicitud de Cores enviada exitosamente!',
                'category': 'success',
                'webhook_data': webhook_response 
            }), 200
        
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error al enviar a webhook de Cores: {e}", exc_info=True)
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

    # Método GET: simplemente mostrar el formulario
    return render_template('shared_forms/solicitud_cores_form.html',
                            username=user_name_session,
                            proceso_origen_nombre=proceso_origen_nombre,
                            url_volver_proceso=url_volver_proceso,
                            area_solicitante_val=request.args.get('area_solicitante') or (proceso_origen if proceso_origen in ['Extrusion Empaques', 'Impresion Empaques', 'Laminacion', 'Corte', 'Fundas'] else ''),
                            solicitante_id_val=user_id_session,
                            subseccion="Solicitud de Cores")

# La ruta /sheet/monitoreo_cores se mantiene con la lógica de Google Sheets
@shared_bp.route('/sheet/monitoreo_cores')
def monitoreo_cores_sheet():
    user_name_session = session.get('user_name')
    if not user_name_session:
        return redirect(url_for('main.login', next=request.url))

    proceso_origen = request.args.get('origen')
    url_volver_proceso = None
    proceso_origen_nombre = None
    
    origenes_map = {
        'impresion': ('impresion.proceso_impresion_dashboard', 'Impresión'),
        'laminacion': ('laminacion.proceso_laminacion_dashboard', 'Laminación'),
        'corte': ('corte.proceso_corte_dashboard', 'Corte'),
        'extrusion': ('extrusion.proceso_extrusion_dashboard', 'Extrusión'),
        'sellado': ('sellado.proceso_sellado_dashboard', 'Sellado'), # Añadido sellado
    }

    if proceso_origen in origenes_map:
        ruta_blueprint, nombre_proceso = origenes_map[proceso_origen]
        url_volver_proceso = url_for(ruta_blueprint)
        proceso_origen_nombre = nombre_proceso
    else:
        url_volver_proceso = url_for('main.home')
        proceso_origen_nombre = "Inicio"

    # Acceder a la conexión de Google Sheets
    # Esto asume que SHEET_SOLICITUD_CORES se configura en create_app
    sheet = current_app.config.get('SHEET_SOLICITUD_CORES') # Revisa cómo configuras esto si lo usas
    all_records = []
    headers = []

    if sheet is None:
        # Aquí deberías usar jsonify si esta ruta también se accediera por AJAX.
        # Pero si es una página separada, flash está bien.
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