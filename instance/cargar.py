import requests
import json

url = "https://apps.alico-sa.com/webhook/5fa36282-590d-41de-be92-a7597865e4ba"

payload = json.dumps({
  "fecha": "2025-08-26 14:21:00",
  "id_empleado": 201,
  "nombre_empleado": "Pedro López",
  "trabajo": "SE34-003",
  "parte": "Parte C",
  "cliente": "Cliente Y",
  "estructura": "PE/PET",
  "ancho": 350.5,
  "largo": 500.25,
  "fuelle": 15,
  "calibre": 30,
  "velocidad": 120,
  "seal_set": 1.5,
  "speed_set": 2,
  "feed_rate": 0.8,
  "tension_adjustment": 1,
  "tipo_bolsa": "Bolsa de pie",
  "abre_boca": "Sí",
  "cara": 1,
  "fotocelda": "Sí",
  "num_fotoceldas": 2,
  "desc_foto_1": "Sensor de borde",
  "desc_foto_2": "Sensor de corte",
  "desc_foto_3": "código de barras",
  "work_mode": "Automático",
  "color_sensor_fotoc": "Rojo",
  "doble_corte": "No",
  "medida_doblecor": 0,
  "zipper": "Sí",
  "pedido_critico": "No",
  "ubicacion_modulo_1": "Superior",
  "ubicacion_modulo_2": "Inferior",
  "ubicacion_modulo_3": "código de barras",
  "tmodulo1": 150,
  "tmodulo2": 145,
  "tmodulo3": 160,
  "tmodulo4": 155,
  "tmodulo5": 170,
  "tmodulo6": 165,
  "tmodulo7": 180,
  "tmodulo8": 175,
  "tmodulo9": 190,
  "tmodulo10": 185,
  "tmodulo11": 200,
  "tmodulo12": 195,
  "tmodulo13": 210,
  "tmodulo14": 205,
  "tmodulo15": 220,
  "tmodulo16": 215,
  "tmodulo17": 230,
  "tmodulo18": 225,
  "tmodulo19": 240,
  "tmodulo20": 235,
  "tmodulo21": 250,
  "tmodulo22": 245
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)

