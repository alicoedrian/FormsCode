# fabrica_plasticos_visualizacion/app.py

from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from functools import wraps # Para el decorador @login_required

app = Flask(__name__)

app.secret_key = os.urandom(24)

USUARIOS_DEMO = {
    "admin": "0",
    "usuario1": "clave123",
    "planta01": "operador"
}

# --- Decorador para verificar si el usuario ha iniciado sesión ---
def login_required(f):
    @wraps(f) # Preserva metadatos de la función original
    def decorated_function(*args, **kwargs):
        if 'user' not in session: # Si 'user' no está en la información de sesión...
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs) # Si está en sesión, permite el acceso a la función original
    return decorated_function

# --- Rutas de Autenticación ---
@app.route('/', methods=['GET', 'POST']) # Ruta raíz y página de login
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in USUARIOS_DEMO and USUARIOS_DEMO[username] == password:
            session['user'] = username
            flash(f'Bienvenido, {username}!', 'success')
            next_url = request.form.get('next')
            return redirect(next_url or url_for('home'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
            return redirect(url_for('login', next=request.form.get('next')))

    if 'user' in session:
        return redirect(url_for('home'))

    return render_template('login.html', next=request.args.get('next'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('login'))

# --- Ruta Principal del Dashboard (Home) ---
@app.route('/home')
@login_required
def home():
    procesos = [
        {"nombre": "Extrusión", "url": url_for('proceso_extrusion'), "icono": "fas fa-layer-group", "descripcion": "Gestión de parámetros y calidad del film.", "color_icono": "#3498DB"},
        {"nombre": "Impresión", "url": url_for('proceso_impresion_dashboard'), "icono": "fas fa-print", "descripcion": "Formularios, estándares y control de calidad.", "color_icono": "#9B59B6"},
        {"nombre": "Laminación", "url": url_for('proceso_laminacion'), "icono": "fas fa-clone", "descripcion": "Control de adhesivos y unión de materiales.", "color_icono": "#F39C12"},
        {"nombre": "Corte", "url": url_for('proceso_corte'), "icono": "fas fa-cut", "descripcion": "Configuración de medidas y calidad de bordes.", "color_icono": "#E74C3C"},
        {"nombre": "Sellado", "url": url_for('proceso_sellado_dashboard'), "icono": "fas fa-box-open", "descripcion": "Parámetros, calidad y documentación de confección.", "color_icono": "#2ECC71"},
        {"nombre": "Insertadoras", "url": url_for('proceso_insertadoras'), "icono": "fas fa-cogs", "descripcion": "Manejo de accesorios y procesos auxiliares.", "color_icono": "#34495E"},
    ]
    return render_template('home.html', username=session.get('user'), procesos=procesos)

# --- Rutas Específicas del Proceso de Impresión ---
@app.route('/proceso/impresion')
@login_required
def proceso_impresion_dashboard():
    opciones_impresion = [
        {"nombre": "Formulario Ambiental", "url": url_for('proceso_impresion_form_ambiental'), "icono": "fas fa-leaf", "descripcion": "Registro y control de aspectos ambientales."},
        {"nombre": "SOPs", "url": "#", "icono": "fas fa-file-alt", "descripcion": "Procedimientos Operativos Estándar (en desarrollo)."},
        {"nombre": "Control de Calidad", "url": "#", "icono": "fas fa-check-circle", "descripcion": "Documentos y guías de calidad (en desarrollo)."},
    ]
    return render_template('processes/impresion_dashboard.html',
                           username=session.get('user'),
                           opciones=opciones_impresion,
                           nombre_proceso="Impresión")

@app.route('/proceso/impresion/formulario_ambiental')
@login_required
def proceso_impresion_form_ambiental():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSdtB1HUXrQz7e5EfO_aKSUi-11bqCnT96_pf2ZR0kE9n8wvoQ/viewform?embedded=true"
    return render_template('processes/impresion_form_ambiental.html',
                           username=session.get('user'),
                           nombre_proceso="Impresión",
                           subseccion="Formulario Ambiental",
                           formulario_url=formulario_url,
                           url_volver=url_for('proceso_impresion_dashboard'))

# --- Rutas Específicas del Proceso de Sellado ---
@app.route('/proceso/sellado')
@login_required
def proceso_sellado_dashboard():
    opciones_sellado = [
        {"nombre": "Estándares de Máquina", "url": url_for('proceso_sellado_form_estandares'), "icono": "fas fa-cogs", "descripcion": "Registro y consulta de parámetros estándar de máquinas."},
        {"nombre": "Control de Calidad", "url": "#", "icono": "fas fa-clipboard-check", "descripcion": "Formatos y guías de calidad para sellado (en desarrollo)."},
    ]
    return render_template('processes/sellado_dashboard.html',
                           username=session.get('user'),
                           opciones=opciones_sellado,
                           nombre_proceso="Sellado")

@app.route('/proceso/sellado/estandares_maquina')
@login_required
def proceso_sellado_form_estandares():
    formulario_url = "https://docs.google.com/forms/d/e/1FAIpQLSeJtdN1LxC0kd0HjCBEjaaMBHNXiF02H_tBdmE-4JokmswvkQ/viewform?embedded=true"
    return render_template('processes/sellado_form_estandares.html',
                           username=session.get('user'),
                           nombre_proceso="Sellado",
                           subseccion="Estándares de Máquina",
                           formulario_url=formulario_url,
                           url_volver=url_for('proceso_sellado_dashboard'))

# --- Rutas Placeholder para OTROS procesos (redirigen a home con mensaje) ---
@app.route('/proceso/extrusion')
@login_required
def proceso_extrusion():
    flash("La sección de Extrusión está en desarrollo. ¡Vuelve pronto!", "info")
    return redirect(url_for('home'))

@app.route('/proceso/laminacion')
@login_required
def proceso_laminacion():
    flash("La sección de Laminación está en desarrollo. ¡Vuelve pronto!", "info")
    return redirect(url_for('home'))

@app.route('/proceso/corte')
@login_required
def proceso_corte():
    flash("La sección de Corte está en desarrollo. ¡Vuelve pronto!", "info")
    return redirect(url_for('home'))

@app.route('/proceso/insertadoras')
@login_required
def proceso_insertadoras():
    flash("La sección de Insertadoras está en desarrollo. ¡Vuelve pronto!", "info")
    return redirect(url_for('home'))

# --- Manejadores de errores ---
@app.errorhandler(404)
def page_not_found(e):
    user_logged_in = 'user' in session
    flash("La página que buscas no existe (Error 404).", "warning")
    return redirect(url_for('home' if user_logged_in else 'login'))

@app.errorhandler(500)
def internal_server_error(e):
    user_logged_in = 'user' in session
    # Considera loguear el error 'e' para depuración en el servidor
    # app.logger.error(f"Error interno del servidor: {e}", exc_info=True)
    flash("Ocurrió un error interno en el servidor (Error 500). Por favor, intenta más tarde o contacta al administrador.", "danger")
    return redirect(url_for('home' if user_logged_in else 'login'))

# --- Punto de entrada para ejecutar la aplicación ---
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)