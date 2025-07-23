import requests
import json

url = "https://apps.alico-sa.com/webhook/02684b4e-f64c-400d-987b-bfd17888b6bc"

payload = json.dumps({
  "fecha": "2025-07-11T14:18:00-05:00",
  "id_empleado": 11283,
  "nombre_empleado": "Juan Carlos Vélez",
  "trabajo": "OP-54321",
  "parte": "Parte A - Lado Izquierdo",
  "cliente": "Supermercados Éxito",
  "estructura": "PET 12 / TINTA / PEBD 70",
  "ancho": 750.5,
  "largo": 300,
  "fuelle": 25.5,
  "calibre": 85,
  "length_set": 299.8,
  "speed_set": 120,
  "feed_rate": 98.5,
  "tension_adjustment": 45,
  "seal_time": 2,
  "mark_sensing_range": 5.5,
  "group_conveying_time": 10,
  "velocidad": 118,
  "work_mode": "Automático",
  "cutter_set": "Cuchilla Superior",
  "skip_mode": "Desactivado",
  "mark_missing_stop": "Activado",
  "selladores_transversales": 150,
  "selladores_longitudinales": 145,
  "fotocelda": "Activada",
  "fotocelda_otro": "Sensor Externo #2",
  "cortasolapa": "Sí",
  "formato": "Sello de Fondo",
  "tmodulo1": 151,
  "tmodulo2": 150,
  "tmodulo3": 152,
  "tmodulo4": 149,
  "tmodulo5": 150,
  "tmodulo6": 151,
  "tmodulo7": 150,
  "tmodulo8": 150,
  "tmodulo9": 152,
  "tmodulo10": 151,
  "tmodulo11": 149,
  "tmodulo12": 150
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)
