# d:\DocumentacionEmpaques\mi_aplicacion\__init__.py

from flask import Flask
import os
from dotenv import load_dotenv

# Importar tus blueprints
from .blueprints.main import main_bp
from .blueprints.laminacion import laminacion_bp
from .blueprints.shared_forms import shared_bp
from .blueprints.impresion import impresion_bp
from .blueprints.corte import corte_bp
from .blueprints.extrusion import extrusion_bp
from .blueprints.sellado import sellado_bp
from .blueprints.empalme_turno import empalme_turno_bp

# from .blueprints.insertadoras import insertadoras_bp # Descomentar si implementas este blueprint

def create_app():
    app = Flask(__name__)
    
    # Cargar variables de entorno una sola vez al inicio de la app
    load_dotenv()

    # Configuración de la aplicación
    app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_for_dev')
    app.config['EPICOR_API_TOKEN'] = os.getenv('EPICOR_API_TOKEN')
    app.config['EPICOR_API_BASE_URL'] = os.getenv('EPICOR_API_BASE_URL')
    app.config['WEBHOOK_URL'] = os.getenv('WEBHOOK_URL')
    app.config['WEBHOOK_AUTH'] = os.getenv('WEBHOOK_AUTH')
    app.config['WEBHOOK_CORES_URL'] = os.getenv('WEBHOOK_CORES_URL')
    app.config['WEBHOOK_CORES_AUTH'] = os.getenv('WEBHOOK_CORES_AUTH')
    
    # Configuraciones específicas para el webhook de Empalme de Turno
    app.config['WEBHOOK_EMP_TURNO_URL'] = os.getenv('WEBHOOK_EMP_TURNO_URL')
    app.config['WEBHOOK_EMP_TURNO_AUTH'] = os.getenv('WEBHOOK_EMP_TURNO_AUTH')

    app.config['TIMEZONE'] = os.getenv('TIMEZONE', 'America/Bogota')

    # Registrar tus blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(laminacion_bp, url_prefix='/laminacion')
    app.register_blueprint(shared_bp, url_prefix='/shared')
    app.register_blueprint(impresion_bp, url_prefix='/impresion')
    app.register_blueprint(corte_bp, url_prefix='/corte')
    app.register_blueprint(extrusion_bp, url_prefix='/extrusion')
    app.register_blueprint(sellado_bp, url_prefix='/sellado')
    app.register_blueprint(empalme_turno_bp, url_prefix='/empalme_turno')

    # app.register_blueprint(insertadoras_bp, url_prefix='/insertadoras')

    return app