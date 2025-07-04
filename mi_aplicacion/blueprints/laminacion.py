import os
import requests
from flask import (
    Blueprint, render_template, request, jsonify, session, 
    current_app, url_for, redirect
)
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

laminacion_bp = Blueprint('laminacion', __name__,
                         template_folder='../templates',
                         static_folder='../static',
                         url_prefix='/laminacion')

# Configuración del webhook externo
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_AUTH = os.getenv('WEBHOOK_AUTH')

if not WEBHOOK_URL or not WEBHOOK_AUTH:
    raise RuntimeError("Faltan variables de entorno requeridas para el webhook")

@laminacion_bp.route('/dashboard')
def proceso_laminacion_dashboard():
    opciones = [{
        "nombre": "Relación de Mezclas", 
        "url": url_for('laminacion.proceso_laminacion_form_mezclas'), 
        "icono": "fas fa-flask", 
        "descripcion": "Registrar nueva mezcla de adhesivos."
    }, {
        # === AÑADIR ESTA OPCIÓN ===
        "nombre": "Solicitud de Cores",
        # El origen es 'laminacion' para que el breadcrumb sepa de dónde viene
        "url": url_for('shared_forms.solicitud_cores_form', origen='laminacion'), 
        "icono": "fas fa-tape", 
        "descripcion": "Solicitar cores para el proceso de Laminación." # Descripción específica
    }]
    return render_template(
        'processes/laminacion/laminacion_dashboard.html',
        nombre_proceso="Laminación",
        username=session.get('user_name'),
        opciones=opciones
    )
def enviar_a_webhook_externo(datos):
    """Envía datos al webhook externo con manejo de SSL"""
    try:
        payload = {
            "maquina": datos['maquina'],
            "turno": datos['turno'],
            "operario_responsable": datos['operario_responsable'],
            "peso_adhesivo": float(datos['peso_adhesivo']),
            "peso_correactante": float(datos['peso_correactante']),
            "relacion_mezcla": float(datos['relacion_mezcla']),
            "id_empleado": session.get('user_id'),
            "id_name": session.get('user_name')
        }
       
        headers = {
            'Content-Type': 'application/json',
            'Authorization': WEBHOOK_AUTH
        }
       
        try:
            response = requests.post(
                WEBHOOK_URL,
                headers=headers,
                json=payload,
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            return response.json()
           
        except requests.exceptions.SSLError:
            response = requests.post(
                WEBHOOK_URL,
                headers=headers,
                json=payload,
                timeout=5,
                verify=False
            )
            response.raise_for_status()
            return response.json()
           
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error enviando al webhook: {str(e)}")
        raise
    except ValueError as e:
        current_app.logger.error(f"Error procesando respuesta: {str(e)}")
        raise

@laminacion_bp.route('/relacion_mezclas', methods=['GET', 'POST'])
def proceso_laminacion_form_mezclas():
    if request.method == 'GET':
        # Mostrar notificación si existe
        notification = request.args.get('notification')
        return render_template(
            'processes/laminacion/laminacion_form_mezclas.html',
            nombre_proceso="Laminación",
            subseccion="Relación de Mezclas",
            username=session.get('user_name'),
            url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
            notification=notification
        )
    
    try:
        datos = request.form.to_dict()
        
        # Validación de campos
        campos_requeridos = [
            'maquina', 'turno', 'operario_responsable',
            'peso_adhesivo', 'peso_correactante', 'relacion_mezcla'
        ]
        
        faltantes = [campo for campo in campos_requeridos if campo not in datos]
        if faltantes:
            return render_template(
                'processes/laminacion/laminacion_form_mezclas.html',
                nombre_proceso="Laminación",
                subseccion="Relación de Mezclas",
                username=session.get('user_name'),
                url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
                notification={
                    'message': f'Faltan campos requeridos: {", ".join(faltantes)}',
                    'category': 'danger'
                }
            )

        # Procesamiento de datos
        peso_adhesivo = float(datos['peso_adhesivo'])
        peso_correactante = float(datos['peso_correactante'])
        relacion_calculada = peso_adhesivo / peso_correactante
        
        # Enviar a webhook
        respuesta_webhook = enviar_a_webhook_externo(datos)
        current_app.logger.info(f"Respuesta webhook: {respuesta_webhook}")
        
        # Redirigir a confirmación con parámetros
        return redirect(url_for(
            'laminacion.confirmacion_registro',
            maquina=datos['maquina'],
            turno=datos['turno'],
            operario=datos['operario_responsable'],
            relacion=f"{round(relacion_calculada, 2)}:1",
            timestamp=respuesta_webhook.get('marca_temporal', '')
        ))

    except ValueError as e:
        current_app.logger.error(f"Error en valores: {str(e)}")
        return render_template(
            'processes/laminacion/laminacion_form_mezclas.html',
            nombre_proceso="Laminación",
            subseccion="Relación de Mezclas",
            username=session.get('user_name'),
            url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
            notification={
                'message': 'Error: Valores numéricos no válidos',
                'category': 'danger'
            }
        )
    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"Error webhook: {str(e)}")
        return render_template(
            'processes/laminacion/laminacion_form_mezclas.html',
            nombre_proceso="Laminación",
            subseccion="Relación de Mezclas",
            username=session.get('user_name'),
            url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
            notification={
                'message': 'Error al conectar con sistema externo',
                'category': 'danger'
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error interno: {str(e)}")
        return render_template(
            'processes/laminacion/laminacion_form_mezclas.html',
            nombre_proceso="Laminación",
            subseccion="Relación de Mezclas",
            username=session.get('user_name'),
            url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
            notification={
                'message': 'Error interno del servidor',
                'category': 'danger'
            }
        )

@laminacion_bp.route('/confirmacion_registro')
def confirmacion_registro():
    """Página de confirmación de registro exitoso"""
    return render_template(
        'processes/laminacion/confirmacion_registro.html',
        nombre_proceso="Laminación",
        subseccion="Confirmación de Registro",
        username=session.get('user_name'),
        maquina=request.args.get('maquina'),
        turno=request.args.get('turno'),
        operario=request.args.get('operario'),
        relacion=request.args.get('relacion'),
        timestamp=request.args.get('timestamp'),
        url_volver=url_for('laminacion.proceso_laminacion_dashboard'),
        url_nuevo=url_for('laminacion.proceso_laminacion_form_mezclas')
    )