import requests
import json

url = "https://apps.alico-sa.com/webhook/455ef59d-441e-44f6-b80e-d46354512137"

payload = json.dumps({
  "fecha": "2025-09-01 14:00:00",
  "id_empleado": 301,
  "nombre_empleado": "Luis García",
  "trabajo": "SE35-001",
  "parte": "Parte D",
  "cliente": "Empresa Z",
  "estructura": "PET/AL/LDPE",
  "ancho": 450.5,
  "largo": 600,
  "fuelle": 20,
  "calibre": 40,
  "velocidad": 135,
  "seal_set": 2,
  "speed_set": 2.5,
  "feed_rate": 0.9,
  "tension_adjustment": 2,
  "tipo_bolsa": "Bolsa de 3 sellos",
  "abre_boca": "No",
  "cara": 2,
  "fotocelda": "Sí",
  "num_fotoceldas": 1,
  "desc_foto_1": "Sensor de registro",
  "desc_foto_2": None,
  "desc_foto_3": None,
  "work_mode": "Manual",
  "color_sensor_fotoc": "Azul",
  "doble_corte": "No",
  "medida_doblecor": 0,
  "zipper": "No",
  "pedido_critico": "Sí",
  "ubicacion_modulo_1": "Lateral",
  "ubicacion_modulo_2": None,
  "ubicacion_modulo_3": None,
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
  "tmodulo22": 245,
  "observaciones": "Hola"
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)