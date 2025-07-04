import requests

url = "https://apps.alico-sa.com/webhook/746f0da9-6f13-4cbd-810b-a974f4bedab1"

payload = {}
headers = {
  'Authorization': 'Basic YWRtaW46SG0xMTkxOTI5'
}

response = requests.request("GET", url, headers=headers, data=payload, verify=False)

print(response.text)