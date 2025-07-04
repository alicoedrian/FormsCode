import requests
import json

url = "https://apps.alico-sa.com/webhook/d1edef27-4534-44a7-bffd-c7f48b22e2c5"

payload = json.dumps({
  "maquina": "LA03 - ITALAM",
  "turno": "TURNO 2 (9:30PM - 5:30AM)",
  "operario_responsable": "FAUSTO ELÍAS RÍOS",
  "peso_adhesivo": 5.54,
  "peso_correactante": 4.44,
  "relacion_mezcla": 1.25,
  "id_empleado": 11565,
  "id_name": "HERNAN M PABON" 
})
headers = {
  'Content-Type': 'application/json'
}

response = requests.request("POST", url, headers=headers, data=payload, verify=False)


print(response.text)
