import requests
import json

url = "https://apps.alico-sa.com/webhook/f4763f3a-6a22-4cc1-b88b-8b77a755c628"

payload = json.dumps({
  "fecha": "2025-09-12",
  "id_empleado": 601,
  "nombre_empleado": "Ricardo Mena",
  "trabajo": "SE26-001",
  "parte": "Parte H",
  "cliente": "Empresa Gamma",
  "estructura": "PET/PE",
  "ancho": 350.5,
  "largo": 580,
  "fuelle": 15,
  "calibre": 30,
  "velocidad": 105,
  "seal_set": 1.2,
  "speed_set": 2,
  "feed_rate": 0.7,
  "tension_adjustment": 1,
  "tipo_bolsa": "Bolsa de 3 sellos",
  "abre_boca": "No",
  "cara": 1,
  "fotocelda": "Sí",
  "num_fotoceldas": 1,
  "desc_foto_1": "Sensor de registro superior",
  "desc_foto_2": None,
  "desc_foto_3": None,
  "work_mode": "Automático",
  "color_sensor_fotoc": "Azul",
  "doble_corte": "No",
  "medida_doblecor": 0,
  "zipper": "Sí",
  "pedido_critico": "No",
  "ubicacion_modulo_1": "Inferior",
  "ubicacion_modulo_2": None,
  "ubicacion_modulo_3": None,
  "tmodulo1": 150,
  "tmodulo2": 155,
  "tmodulo3": 160,
  "tmodulo4": 165,
  "tmodulo5": 170,
  "tmodulo6": 175,
  "tmodulo7": 180,
  "tmodulo8": 185,
  "tmodulo9": 190,
  "tmodulo10": 195,
  "tmodulo11": 200,
  "tmodulo12": 205,
  "tmodulo13": 210,
  "tmodulo14": 215,
  "tmodulo15": 220,
  "tmodulo16": 225,
  "tmodulo17": 230,
  "tmodulo18": 235,
  "tmodulo19": 240,
  "tmodulo20": 245,
  "tmodulo21": 250,
  "tmodulo22": 255,
  "observaciones": "Se realizó mantenimiento preventivo antes del inicio del turno."
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)