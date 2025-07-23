# d:\DocumentacionEmpaques\mi_aplicacion\blueprints\almacen_taras\almacen_taras.py

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, current_app, jsonify
)
import psycopg2 # Para la conexión a PostgreSQL
from werkzeug.security import generate_password_hash, check_password_hash # Para hashing de contraseñas
import os # Para acceder a variables de entorno

# --- Blueprint Setup ---
almacen_taras_bp = Blueprint('almacen_taras', __name__,
                             template_folder='../../../templates', # Subir hasta mi_aplicacion/templates
                             static_folder='../../../static',     # Subir hasta mi_aplicacion/static
                             url_prefix='/almacen')

# --- Helper function for DB connection ---
def get_db_connection():
    """
    Establece y devuelve una conexión a la base de datos PostgreSQL.
    Las credenciales se obtienen de las variables de entorno.
    """
    try:
        conn = psycopg2.connect(
            dbname=os.getenv('PG_DBNAME'),
            user=os.getenv('PG_USER'),
            password=os.getenv('PG_PASSWORD'),
            host=os.getenv('PG_HOST'),
            port=os.getenv('PG_PORT')
        )
        return conn
    except Exception as e:
        current_app.logger.error(f"Error al conectar con la base de datos PostgreSQL: {e}", exc_info=True)
        return None

# --- Decorador para proteger rutas del módulo Almacén Taras ---
def login_required_almacen(f):
    """
    Decorador que asegura que el usuario ha iniciado sesión en el módulo de Almacén Taras.
    Redirige a la página de login de Almacén si no está autenticado.
    """
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'almacen_logged_in' not in session or not session['almacen_logged_in']:
            flash('Acceso denegado. Por favor, inicia sesión en Almacén Taras.', 'danger')
            return redirect(url_for('almacen_taras.almacen_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas para el Módulo Almacén Taras ---

@almacen_taras_bp.route('/login', methods=['GET', 'POST'])
def almacen_login():
    """
    Maneja el inicio de sesión para el módulo de Almacén Taras (usuario y contraseña).
    """
    if 'almacen_logged_in' in session and session['almacen_logged_in']:
        # Si ya está logueado, redirige al dashboard o a la URL 'next'
        next_url = request.args.get('next') or url_for('almacen_taras.almacen_dashboard')
        return redirect(next_url)

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_url = request.form.get('next') # Campo oculto en el formulario para redirigir después del login

        if not username or not password:
            flash('Usuario y contraseña son requeridos.', 'warning')
            return render_template('almacen_taras/almacen_login.html', next=next_url)

        conn = get_db_connection()
        if conn is None:
            flash('Error de conexión a la base de datos.', 'danger')
            return render_template('almacen_taras/almacen_login.html', next=next_url)

        try:
            with conn.cursor() as cur:
                # Busca el usuario por nombre de usuario
                cur.execute("SELECT id, username, password_hash FROM almacen_users WHERE username = %s", (username,))
                user = cur.fetchone()
            
            # Verifica si el usuario existe y si la contraseña coincide con el hash almacenado
            if user and check_password_hash(user[2], password): # user[2] es password_hash
                session['almacen_logged_in'] = True # Marca la sesión como autenticada para Almacén
                session['almacen_user_id'] = user[0] # Guarda el ID del usuario de Almacén
                session['almacen_username'] = user[1] # Guarda el nombre de usuario de Almacén
                flash(f'Bienvenido al módulo de Almacén Taras, {user[1]}!', 'success')
                return redirect(next_url or url_for('almacen_taras.almacen_dashboard'))
            else:
                flash('Usuario o contraseña incorrectos.', 'danger')
        except Exception as e:
            current_app.logger.error(f"Error durante el login de Almacén Taras para el usuario {username}: {e}", exc_info=True)
            flash('Ocurrió un error al intentar iniciar sesión.', 'danger')
        finally:
            if conn:
                conn.close() # Asegura que la conexión a la DB se cierre

    # Renderiza la plantilla del formulario de login
    return render_template('almacen_taras/almacen_login.html', next=request.args.get('next'))


@almacen_taras_bp.route('/dashboard')
@login_required_almacen # Protege esta ruta con el decorador
def almacen_dashboard():
    """
    Página principal del módulo de Almacén Taras (protegida).
    """
    return render_template('almacen_taras/almacen_dashboard.html',
                           username_almacen=session.get('almacen_username'),
                           nombre_proceso="Almacén Taras",
                           subseccion="Dashboard")

@almacen_taras_bp.route('/logout')
def almacen_logout():
    """
    Cierra la sesión específica del módulo de Almacén Taras.
    """
    session.pop('almacen_logged_in', None)
    session.pop('almacen_user_id', None)
    session.pop('almacen_username', None)
    flash('Has cerrado sesión del módulo de Almacén Taras.', 'info')
    return redirect(url_for('almacen_taras.almacen_login'))

# Ejemplo de ruta protegida dentro de Almacén Taras
@almacen_taras_bp.route('/gestion_taras')
@login_required_almacen # Esta ruta también requiere autenticación de Almacén
def gestion_taras():
    """
    Página de gestión de taras dentro del módulo de Almacén (protegida).
    """
    return render_template('almacen_taras/gestion_taras.html',
                           username_almacen=session.get('almacen_username'),
                           nombre_proceso="Almacén Taras",
                           subseccion="Gestión de Taras")