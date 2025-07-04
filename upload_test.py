import requests
import json
import wave
import os

BACKEND_URL = "http://localhost:8000"

def check_backend_alive():
    print("1) Comprobando si backend responde a /roleplays ...")
    try:
        resp = requests.get(f"{BACKEND_URL}/roleplays", timeout=5)
        print(f" Código HTTP: {resp.status_code}")
        if resp.status_code == 200:
            print(" Backend está activo y responde correctamente.")
            return True
        else:
            print(" Backend respondió, pero con error.")
            print(resp.text)
            return False
    except Exception as e:
        print(f" Error conectando al backend: {e}")
        return False

def create_test_audio(filename="test_audio.wav"):
    print("2) Creando audio WAV de prueba muy pequeño ...")
    try:
        with wave.open(filename, 'w') as wf:
            wf.setnchannels(1)      # mono
            wf.setsampwidth(2)      # 2 bytes por sample
            wf.setframerate(8000)   # 8kHz sample rate
            wf.writeframes(b'\x00\x00' * 8000)  # 1 segundo silencio
        print(f" Audio creado: {filename}")
        return filename
    except Exception as e:
        print(f" Error creando audio: {e}")
        return None

def test_upload_audio(audio_path):
    print("3) Probando subir audio de prueba con POST /upload ...")
    data = {
        "comprador": "Tester",
        "vendedor": "Tester",
        "productos": json.dumps(["test_product"]),
        "costes": json.dumps(["0.01"])
    }
    files = {
        "audio": (os.path.basename(audio_path), open(audio_path, "rb"), "audio/wav")
    }

    try:
        resp = requests.post(f"{BACKEND_URL}/upload", data=data, files=files, timeout=10)
        print(f" Código HTTP: {resp.status_code}")
        try:
            resp_json = resp.json()
            print(" Respuesta JSON:", resp_json)
            if resp.status_code == 200 and resp_json.get("status") == "ok":
                print(" Subida de audio correcta.")
                return True
            else:
                print(" La subida no fue correcta.")
                return False
        except Exception as e:
            print(f" Error leyendo JSON de respuesta: {e}")
            print("Respuesta completa:", resp.text)
            return False
    except Exception as e:
        print(f" Error en la petición POST /upload: {e}")
        return False
    finally:
        files["audio"][1].close()

if __name__ == "__main__":
    print("=== TEST DE CONEXIÓN Y SUBIDA DE AUDIO ===\n")

    if not check_backend_alive():
        print("\n> El backend no está disponible. Arranca el servidor FastAPI y prueba de nuevo.")
        exit(1)

    audio_file = create_test_audio()
    if not audio_file:
        print("\n> No se pudo crear audio de prueba. Abortando.")
        exit(1)

    success = test_upload_audio(audio_file)

    if success:
        print("\n> Test completado con éxito. El backend acepta uploads correctamente.")
    else:
        print("\n> Test fallido. Revisa los logs del backend y la configuración de la app.")

    # Opcional: eliminar audio de prueba
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)
