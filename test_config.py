import requests

CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
# o usa 'master' si tu rama es master

try:
    resp = requests.get(CONFIG_URL, timeout=5)
    print("Status:", resp.status_code)
    print("Contenido:", resp.text)
except Exception as e:
    print("Error al obtener config.json:", e)
