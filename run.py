# /run.py

from mi_aplicacion import create_app

# Creamos una instancia de la aplicación usando la factory
app = create_app()

if __name__ == '__main__':
    # Usar host='0.0.0.0' para que sea accesible en tu red local.
    app.run(debug=True, host='0.0.0.0', port=5001)