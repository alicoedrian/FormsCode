import requests
import json

url = "https://apps.alico-sa.com/webhook/75a8eac2-1ffe-4e57-a315-354f0cff7340"

payload = json.dumps({
  "Fecha": "2025-08-13 10:00:00",
  "Id_empleado": 101,
  "Nombre_empleado": "Edrian Escobar",
  "Trabajo": "SE50-001",
  "Parte": "Parte A",
  "Cliente": "Cliente XYZ",
  "Estructura": "PET/LDPE",
  "Ancho": 500.5,
  "Largo": 750.75,
  "Fuelle": 25,
  "Calibre": 45,
  "Velocidad": 150,
  "Ajuste_longitud": 1.25,
  "Tiempo_avance": 0.5,
  "Tiempo_sello": 0.75,
  "Tiempo_estabilizacion": 0.25,
  "Velocidad_teorica": 160,
  "Velocidad_real": 155,
  "Tiempo_perforacion": 0.1,
  "Longitud_secundaria": 200,
  "Marca_3": 1,
  "Compens_avance": 5,
  "Ajuste velocidad": 100,
  "Ciclo avance": 200,
  "Modo Trabajo": "Manual",
  "Modo saltar": "Desactivado",
  "Modo perforacion": "Activado",
  "Modo Pouch": "Doypack",
  "Rodillo_servo1_der": 10.5,
  "Rodillo_servo1_izq": 10.5,
  "Rodillo_servo2_der": 11,
  "Rodillo_servo2_izq": 11,
  "Rodillo_servo3_der": 12,
  "Rodillo_servo3_izq": 12,
  "Rodillo_servo4_der": 15,
  "Rodillo_servo4_izq": 15,
  "Balancin_1": 2.5,
  "Balancin_2": 3,
  "Balancin_3_doypack": 1.5,
  "Freno_rodillo": 4,
  "Sellador_valvulas_preselle_superior_1": 150,
  "Sellador_valvulas_preselle_inferior_2": 145,
  "Sellador_transversal_superior_9": 160,
  "Sellador_transversal_inferior_10": 155,
  "Sellador_transversal_superior_11": 165,
  "Sellador_transversal_inferior_12": 160,
  "Sellador_transversal_superior_13": 170,
  "Sellador_transversal_inferior_14": 165,
  "Sellador_transversal_superior_15": 175,
  "Sellador_transversal_inferior_16": 170,
  "Sellador_longitudinal_superior_17": 180,
  "Sellador_longitudinal_inferior_18": 175,
  "Sellador_longitudinal_superior_19": 185,
  "Sellador_longitudinal_inferior_20": 180,
  "Sellador_longitudinal_superior_21": 190,
  "Sellador_longitudinal_inferior_22": 185
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("POST", url, headers=headers, data=payload, verify=False)

print(response.text)
