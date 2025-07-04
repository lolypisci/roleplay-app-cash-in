import sounddevice as sd
import numpy as np
import time

def test_audio_record_and_playback():
    duration = 3  # segundos
    fs = 44100
    channels = 1
    print("Grabando audio durante 3 segundos...")
    try:
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=channels)
        sd.wait()  # Espera a que termine la grabación
        print("Grabación terminada, reproduciendo...")
        sd.play(recording, fs)
        sd.wait()  # Espera a que termine la reproducción
        print("Reproducción terminada sin errores.")
    except Exception as e:
        print("Error en grabar o reproducir audio:", e)

if __name__ == "__main__":
    test_audio_record_and_playback()
