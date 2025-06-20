import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox
import requests
import io
import json

# ==================== CONFIG AUTOMÁTICA ====================
# URL raw de tu config.json en GitHub (sin token en la URL):
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"

def obtener_backend_url():
    try:
        resp = requests.get(CONFIG_URL, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            url = data.get("backend_url", "").strip()
            if url:
                print(f"[Config] Usando backend URL desde config.json: {url}")
                return url
            else:
                print("[Config] El campo 'backend_url' está vacío en config.json.")
        else:
            print(f"[Config] No se pudo obtener config.json (status {resp.status_code}).")
    except Exception as e:
        print(f"[Config] Error al descargar config.json: {e}")
    # Fallback: pedir al usuario
    url_input = input("Enter backend URL (e.g. https://xxxx.ngrok-free.app): ").strip()
    return url_input

# Obtén BACKEND_URL automáticamente:
BACKEND_URL = obtener_backend_url()
# ===========================================================

# Parámetros de grabación
SAMPLE_RATE = 44100  # Frecuencia de muestreo
CHANNELS = 1         # Mono

class Recorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.stream = None

    def start(self):
        self.frames = []
        self.recording = True
        def callback(indata, frames, time, status):
            if self.recording:
                self.frames.append(indata.copy())
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=CHANNELS,
                callback=callback
            )
            self.stream.start()
        except Exception as e:
            messagebox.showerror("Error", f"Error accessing microphone:\n{e}")
            self.recording = False

    def stop(self):
        if not self.recording:
            return None
        self.recording = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except:
                pass
        if not self.frames:
            return None
        data = np.concatenate(self.frames, axis=0)
        return data


def encode_wav(data: np.ndarray, samplerate: int) -> bytes:
    """Codifica un array numpy mono (float32) a WAV 16-bit PCM y retorna bytes."""
    int_data = np.int16(np.clip(data, -1, 1) * 32767)
    buffer = io.BytesIO()
    wf = wave.open(buffer, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)
    wf.setframerate(samplerate)
    wf.writeframes(int_data.tobytes())
    wf.close()
    return buffer.getvalue()

class App:
    def __init__(self, root):
        self.root = root
        root.title("Roleplay Archive: Cash In - Student")
        # Widgets
        tk.Label(root, text="Buyer Name:").grid(row=0, column=0, sticky="e")
        self.entry_buyer = tk.Entry(root, width=30)
        self.entry_buyer.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(root, text="Seller Name:").grid(row=1, column=0, sticky="e")
        self.entry_seller = tk.Entry(root, width=30)
        self.entry_seller.grid(row=1, column=1, padx=5, pady=5)

        self.btn_start = tk.Button(root, text="Start Recording", command=self.start_recording)
        self.btn_start.grid(row=2, column=0, padx=5, pady=5)

        self.btn_stop = tk.Button(root, text="Stop Recording", command=self.stop_recording, state="disabled")
        self.btn_stop.grid(row=2, column=1, padx=5, pady=5)

        tk.Label(root, text="Purchase Details:").grid(row=3, column=0, sticky="ne")
        self.text_products = tk.Text(root, width=40, height=4)
        self.text_products.grid(row=3, column=1, padx=5, pady=5)

        self.btn_submit = tk.Button(root, text="Submit Roleplay", command=self.submit, state="disabled")
        self.btn_submit.grid(row=4, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(root, text="")
        self.status_label.grid(row=5, column=0, columnspan=2)

        self.recorder = Recorder()
        self.audio_data = None

    def start_recording(self):
        buyer = self.entry_buyer.get().strip()
        seller = self.entry_seller.get().strip()
        if not buyer or not seller:
            messagebox.showwarning("Warning", "Please enter buyer and seller names.")
            return
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.status_label.config(text="Recording...")
        threading.Thread(target=self.recorder.start, daemon=True).start()

    def stop_recording(self):
        data = self.recorder.stop()
        if data is None or data.size == 0:
            messagebox.showwarning("Warning", "No audio recorded.")
            self.btn_start.config(state="normal")
            self.btn_stop.config(state="disabled")
            return
        self.audio_data = data
        self.status_label.config(text="Recording stopped.")
        self.btn_submit.config(state="normal")
        self.btn_stop.config(state="disabled")

    def submit(self):
        buyer = self.entry_buyer.get().strip()
        seller = self.entry_seller.get().strip()
        products_text = self.text_products.get("1.0", tk.END).strip()
        if not products_text:
            messagebox.showwarning("Warning", "Please enter products and prices.")
            return
        if self.audio_data is None:
            messagebox.showwarning("Warning", "No recording to submit.")
            return
        try:
            wav_bytes = encode_wav(self.audio_data, SAMPLE_RATE)
        except Exception as e:
            messagebox.showerror("Error", f"Error encoding WAV:\n{e}")
            return
        products_arr = []
        for item in products_text.split(","):
            parts = item.split(":")
            if len(parts) == 2:
                name = parts[0].strip()
                try:
                    price = float(parts[1].strip())
                except:
                    price = 0.0
                products_arr.append({"nombre": name, "precio": price})
        def do_upload():
            try:
                files = {
                    "audio": ("roleplay.wav", wav_bytes, "audio/wav")
                }
                data = {
                    "comprador": buyer,
                    "vendedor": seller,
                    "productos_json": json.dumps(products_arr)
                }
                url = BACKEND_URL.rstrip("/") + "/upload"
                resp = requests.post(url, data=data, files=files, timeout=30)
                if resp.status_code == 200:
                    self.status_label.config(text="Submitted successfully.")
                    self.audio_data = None
                    self.btn_submit.config(state="disabled")
                else:
                    messagebox.showerror("Error", f"Upload failed: {resp.status_code}\n{resp.text}")
                    self.status_label.config(text="Upload failed.")
                self.btn_start.config(state="normal")
            except Exception as e:
                messagebox.showerror("Error", f"Network error:\n{e}")
                self.status_label.config(text="Network error.")
                self.btn_start.config(state="normal")
        self.btn_submit.config(state="disabled")
        self.status_label.config(text="Uploading...")
        threading.Thread(target=do_upload, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
