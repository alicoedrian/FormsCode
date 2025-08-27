# d:\DocumentacionEmpaques\mi_aplicacion\__init__.py

from flask import Flask
import os
from dotenv import load_dotenv
import logging # Añade esta importación para el logger
from logging.handlers import RotatingFileHandler # Añade esta importación para el logger

# --- Importar tus blueprints ---
from .blueprints.main import main_bp
from .blueprints.laminacion.laminacion import laminacion_bp
from .blueprints.transversal.shared_forms import shared_bp
from .blueprints.impresion.impresion import impresion_bp
from .blueprints.corte.corte import corte_bp
from .blueprints.extrusion.extrusion import extrusion_bp
from .blueprints.sellado.sellado import sellado_bp
from .blueprints.transversal.empalme_turno import empalme_turno_bp
from .blueprints.sellado.sellado_form_se30_se47 import se30_se47_bp 
from .blueprints.transversal.despeje_linea import despeje_linea_bp
from .blueprints.transversal.monitoreo_cuchillas import monitoreo_cuchillas_bp
from .blueprints.coordinadores.coordinadores import coordinadores_bp
from .blueprints.taras.taras import taras_bp
from .blueprints.sellado.sellado_form_Se50 import se50_bp
from .blueprints.sellado.sellado_form_se34 import se34_bp



def create_app():
    app = Flask(__name__)

    # 1. Cargar variables de entorno del archivo .env
    load_dotenv() 

    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_for_dev')
    app.config['EPICOR_API_TOKEN'] = os.getenv('EPICOR_API_TOKEN')
    app.config['EPICOR_API_BASE_URL'] = os.getenv('EPICOR_API_BASE_URL')
    app.config['WEBHOOK_URL'] = os.getenv('WEBHOOK_URL')
    app.config['WEBHOOK_AUTH'] = os.getenv('WEBHOOK_AUTH') # Carga WEBHOOK_AUTH
    app.config['WEBHOOK_CORES_URL'] = os.getenv('WEBHOOK_CORES_URL')
    app.config['WEBHOOK_CORES_AUTH'] = os.getenv('WEBHOOK_CORES_AUTH')
    app.config['WEBHOOK_EMP_TURNO_URL'] = os.getenv('WEBHOOK_EMP_TURNO_URL')
    app.config['WEBHOOK_EMP_TURNO_AUTH'] = os.getenv('WEBHOOK_EMP_TURNO_AUTH')
    app.config['EPICOR_API_PAUSAS_ACTIVAS'] = os.getenv('EPICOR_API_PAUSAS_ACTIVAS')
    app.config['EPICOR_API_TRABAJOS_FORM'] = os.getenv('EPICOR_API_TRABAJOS_FORM')
    app.config['WEBHOOK_SE30_SE47_URL'] = os.getenv('WEBHOOK_SE30_SE47_URL')
    app.config['WEBHOOK_SE30_SE47_AUTH'] = os.getenv('WEBHOOK_SE30_SE47_AUTH')
    app.config['TIMEZONE'] = os.getenv('TIMEZONE', 'America/Bogota')
    app.config['EPICOR_API_CARNET_LOOKUP'] = os.getenv('EPICOR_API_CARNET_LOOKUP')
    app.config['WEBHOOK_MONITOREO_CUCHILLAS_URL'] = os.getenv('WEBHOOK_MONITOREO_CUCHILLAS_URL')
    app.config['WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION'] = os.getenv('WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION')
    app.config['WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION_COOR'] = os.getenv('WEBHOOK_MONITOREO_CUCHILLAS_URL_VALIDACION_COOR') # Carga la URL del coordinador
    app.config['WEBHOOK_CORES_URL_SELECT'] = os.getenv('WEBHOOK_CORES_URL_SELECT') # Carga la URL del coordinador
    app.config['WEBHOOK_SE50'] = os.getenv('WEBHOOK_SE50')
    app.config['WEBHOOK_SE34_URL'] = os.getenv('WEBHOOK_SE34_URL')
    app.config['WEBHOOK_SE34_AUTH'] = os.getenv('WEBHOOK_SE34_AUTH')



    if not app.logger.handlers:
        file_handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO) # Establece el nivel de logging para la app

    # Registrar tus blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(laminacion_bp, url_prefix='/laminacion')
    app.register_blueprint(shared_bp, url_prefix='/shared')
    app.register_blueprint(impresion_bp, url_prefix='/impresion')
    app.register_blueprint(corte_bp, url_prefix='/corte')
    app.register_blueprint(extrusion_bp, url_prefix='/extrusion')
    app.register_blueprint(sellado_bp, url_prefix='/sellado')
    app.register_blueprint(empalme_turno_bp, url_prefix='/empalme_turno')
    app.register_blueprint(se30_se47_bp) 
    app.register_blueprint(despeje_linea_bp, url_prefix='/shared')
    app.register_blueprint(monitoreo_cuchillas_bp, url_prefix='/shared') 
    app.register_blueprint(coordinadores_bp)
    app.register_blueprint(taras_bp)
    app.register_blueprint(se50_bp)
    app.register_blueprint(se34_bp)


    return app