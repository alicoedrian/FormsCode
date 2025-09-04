import requests
import json

url = "https://apps.alico-sa.com/webhook/cd42f1c3-9cd7-449b-bb9a-49da334f3f05"

payload = json.dumps({
  "fecha": "2025-09-04 15:35:15",
  "id_empleado": 401,
  "nombre_empleado": "Diana López",
  "trabajo": "SE25-001",
  "parte": "Parte F",
  "cliente": "Empresa Omega",
  "estructura": "PET/LDPE",
  "ancho": 380,
  "largo": 525.5,
  "fuelle": 18,
  "calibre": 35,
  "velocidad": 110,
  "seal_set": 1.5,
  "speed_set": 2.2,
  "feed_rate": 0.8,
  "tension_adjustment": 1,
  "tipo_bolsa": "Bolsa de 3 sellos",
  "abre_boca": "No",
  "cara": 1,
  "fotocelda": "Sí",
  "num_fotoceldas": 1,
  "desc_foto_1": "Sensor de borde",
  "desc_foto_2": "None",
  "desc_foto_3": "None",
  "work_mode": "Automático",
  "color_sensor_fotoc": "Rojo",
  "doble_corte": "Sí",
  "medida_doblecor": 125,
  "zipper": "No",
  "pedido_critico": "No",
  "ubicacion_modulo_1": "Izquierda",
  "ubicacion_modulo_2": "None",
  "ubicacion_modulo_3": "None",
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
  "observaciones": "Se hizo un ajuste fino en el sensor para mejor precisión."
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload, verify=False)

print(response.text)