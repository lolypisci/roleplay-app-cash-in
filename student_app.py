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
    
    url_input = input("Enter backend URL (e.g. https://xxxx.ngrok-free.app): ").strip()
    return url_input

BACKEND_URL = obtener_backend_url()
# ===========================================================

SAMPLE_RATE = 44100
CHANNELS = 1

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

        tk.Label(root, text="Purchased Items (separate by commas):").grid(row=3, column=0, sticky="ne")
        self.text_products = tk.Text(root, width=40, height=4)
        self.text_products.grid(row=3, column=1, padx=5, pady=5)

        tk.Label(root, text="Costs (separate by commas):").grid(row=4, column=0, sticky="ne")
        self.text_costs = tk.Text(root, width=40, height=2)
        self.text_costs.grid(row=4, column=1, padx=5, pady=5)

        self.btn_submit = tk.Button(root, text="Submit Roleplay", command=self.submit, state="disabled")
        self.btn_submit.grid(row=5, column=0, columnspan=2, pady=10)

        self.status_label = tk.Label(root, text="")
        self.status_label.grid(row=6, column=0, columnspan=2)

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
        costs_text = self.text_costs.get("1.0", tk.END).strip()

        if not products_text:
            messagebox.showwarning("Warning", "Please enter purchased items.")
            return
        if not costs_text:
            messagebox.showwarning("Warning", "Please enter costs.")
            return
        if self.audio_data is None:
            messagebox.showwarning("Warning", "No recording to submit.")
            return
        try:
            wav_bytes = encode_wav(self.audio_data, SAMPLE_RATE)
        except Exception as e:
            messagebox.showerror("Error", f"Error encoding WAV:\n{e}")
            return

        products_arr = [p.strip() for p in products_text.split(",") if p.strip()]

        costs_arr = []
        for c in costs_text.split(","):
            c = c.strip()
            try:
                costs_arr.append(float(c))
            except:
                costs_arr.append(0.0)

        if len(products_arr) != len(costs_arr):
            messagebox.showwarning("Warning", "The number of purchased items and costs must be the same.")
            return

        def do_upload():
            try:
                files = {"audio": ("roleplay.wav", wav_bytes, "audio/wav")}
                data = {
                    "comprador": buyer,
                    "vendedor": seller,
                    "productos": json.dumps(products_arr),
                    "costes": json.dumps(costs_arr)
                }
                url = BACKEND_URL.rstrip("/") + "/upload"
                resp = requests.post(url, data=data, files=files, timeout=30)
                if resp.status_code == 200:
                    self.status_label.config(text="Submitted successfully.")
                    self.audio_data = None
                    self.btn_submit.config(state="disabled")
                    self.btn_start.config(state="normal")
                    self.text_products.delete("1.0", tk.END)
                    self.text_costs.delete("1.0", tk.END)
                else:
                    messagebox.showerror("Error", f"Upload failed: {resp.status_code}\n{resp.text}")
                    self.status_label.config(text="Upload failed.")
            except Exception as e:
                messagebox.showerror("Error", f"Network error:\n{e}")
                self.status_label.config(text="Network error.")

        self.btn_submit.config(state="disabled")
        self.status_label.config(text="Uploading...")
        threading.Thread(target=do_upload, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
