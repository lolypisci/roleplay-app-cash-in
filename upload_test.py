import requests

url = "http://localhost:8000/upload"
files = {
    "audio": open(r"C:\Users\User\Desktop\Games\d40fd007f88d4031b7015f75328429c3.wav", "rb")
}
data = {
    "comprador": "Juan",
    "vendedor": "Ana",
    "productos": '["manzana","pera"]',
    "costes": '["1.20","0.80"]'
}

resp = requests.post(url, files=files, data=data)
print(resp.status_code)
print(resp.json())
