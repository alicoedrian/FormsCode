# /mi_aplicacion/utils.py

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import current_app

def get_sheet_connection(spreadsheet_id, worksheet_name):
    """
    Establece una conexión a una hoja de cálculo específica de Google Sheets.
    Utiliza la configuración de la aplicación actual de Flask.
    """
    try:
        creds_file = current_app.config['GOOGLE_CREDS_FILE']
        scope = current_app.config['GOOGLE_SCOPE']
        
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file, scope)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet.worksheet(worksheet_name)
    except Exception as e:
        # Usamos el logger de la aplicación para registrar errores, es la práctica correcta.
        current_app.logger.error(f"Error al conectar con Google Sheet '{worksheet_name}': {e}", exc_info=True)
        return None