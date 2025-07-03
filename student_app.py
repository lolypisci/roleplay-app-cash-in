import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageFont
import io
import json
import requests
from datetime import datetime

# Config
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"  # fallback local URL

def get_backend_url():
    try:
        data = requests.get(CONFIG_URL, timeout=5).json()
        url = data.get("backend_url", "").rstrip("/")
        if url:
            return url
        else:
            raise ValueError("Empty backend_url in config")
    except Exception:
        # Si no puede obtener de internet, pedir al usuario con diálogo TK
        root = tk.Tk()
        root.withdraw()
        url = simpledialog.askstring(
            "Backend URL",
            "No se pudo obtener la URL del backend.\nIntroduce la URL del backend Rolefy:",
            initialvalue=DEFAULT_BACKEND
        )
        root.destroy()
        if not url:
            messagebox.showerror("Error", "No se especificó URL de backend. La app se cerrará.")
            exit(1)
        return url.rstrip("/")

BACKEND = get_backend_url()
SAMPLE_RATE, CHANNELS = 44100, 1

class Recorder:
    def __init__(self):
        self.recording = False
        self.frames = []

    def start(self):
        self.frames = []
        self.recording = True
        def callback(indata, frames, time, status):
            if self.recording:
                self.frames.append(indata.copy())
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback)
        self.stream.start()

    def stop(self):
        self.recording = False
        self.stream.stop()
        self.stream.close()
        if self.frames:
            return np.concatenate(self.frames, axis=0)
        return None

def encode_wav(data):
    raw = (np.int16(np.clip(data, -1, 1) * 32767)).tobytes()
    buf = io.BytesIO()
    wf = wave.open(buf, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(2)
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(raw)
    wf.close()
    return buf.getvalue()

class App:
    def __init__(self, root):
        self.root = root
        root.title("Rolefy – Student")

        # UI Layout
        tk.Label(root, text="Buyer:").grid(row=0, column=0, sticky="e")
        self.ebuyer = tk.Entry(root, width=30)
        self.ebuyer.grid(row=0, column=1, padx=5, pady=2)

        tk.Label(root, text="Seller:").grid(row=1, column=0, sticky="e")
        self.eseller = tk.Entry(root, width=30)
        self.eseller.grid(row=1, column=1, padx=5, pady=2)

        tk.Label(root, text="Items (one per line):").grid(row=2, column=0, sticky="ne")
        self.tp = tk.Text(root, height=6, width=30)
        self.tp.grid(row=2, column=1, padx=5, pady=2)

        tk.Label(root, text="Costs (one per line):").grid(row=3, column=0, sticky="ne")
        self.tc = tk.Text(root, height=6, width=30)
        self.tc.grid(row=3, column=1, padx=5, pady=2)

        self.bt_start = tk.Button(root, text="Start Recording", command=self.start_recording)
        self.bt_start.grid(row=4, column=0, pady=10)

        self.bt_stop = tk.Button(root, text="Stop Recording", command=self.stop_recording, state='disabled')
        self.bt_stop.grid(row=4, column=1, pady=10, sticky="w")

        self.bt_submit = tk.Button(root, text="Submit", command=self.submit, state='disabled')
        self.bt_submit.grid(row=5, column=0, columnspan=2, pady=10)

        self.status_lbl = tk.Label(root, text="", fg="blue")
        self.status_lbl.grid(row=6, column=0, columnspan=2)

        self.timer_lbl = tk.Label(root, text="", fg="green")
        self.timer_lbl.grid(row=7, column=0, columnspan=2)

        self.recorder = Recorder()
        self.audio_data = None
        self.recording_seconds = 0
        self.timer_job = None

    def start_recording(self):
        if not self.ebuyer.get().strip() or not self.eseller.get().strip():
            messagebox.showwarning("Faltan datos", "Por favor, introduce los nombres de Buyer y Seller antes de grabar.")
            return
        self.audio_data = None
        self.recording_seconds = 0
        self.status_lbl.config(text="Recording...")
        self.timer_lbl.config(text="00:00")
        self.bt_start.config(state='disabled')
        self.bt_stop.config(state='normal')
        self.bt_submit.config(state='disabled')
        threading.Thread(target=self.recorder.start, daemon=True).start()
        self.update_timer()

    def update_timer(self):
        self.recording_seconds += 1
        mins, secs = divmod(self.recording_seconds, 60)
        self.timer_lbl.config(text=f"{mins:02d}:{secs:02d}")
        self.timer_job = self.root.after(1000, self.update_timer)

    def stop_recording(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
            self.timer_job = None
        data = self.recorder.stop()
        if data is None:
            messagebox.showwarning("No audio", "No se detectó audio grabado.")
            self.status_lbl.config(text="")
            self.bt_start.config(state='normal')
            self.bt_stop.config(state='disabled')
            return
        self.audio_data = data
        self.status_lbl.config(text="Recording stopped.")
        self.bt_start.config(state='normal')
        self.bt_stop.config(state='disabled')
        self.bt_submit.config(state='normal')

    def submit(self):
        items = [line.strip() for line in self.tp.get("1.0", "end").splitlines() if line.strip()]
        costs_text = [line.strip() for line in self.tc.get("1.0", "end").splitlines() if line.strip()]

        if len(items) != len(costs_text):
            messagebox.showwarning("Error", "El número de items y costes no coincide.")
            return
        try:
            costs = [float(c.replace(',', '.')) for c in costs_text]
        except ValueError:
            messagebox.showwarning("Error", "Los costes deben ser números válidos.")
            return

        if self.audio_data is None or self.audio_data.size == 0:
            messagebox.showwarning("Error", "No hay audio para enviar.")
            return

        self.status_lbl.config(text="Uploading...")
        self.bt_submit.config(state='disabled')
        self.bt_start.config(state='disabled')

        wav_data = encode_wav(self.audio_data)
        files = {"audio": ("recording.wav", wav_data, "audio/wav")}
        data = {
            "comprador": self.ebuyer.get().strip(),
            "vendedor": self.eseller.get().strip(),
            "productos": json.dumps(items),
            "costes": json.dumps(costs),
        }

        def do_upload():
            try:
                response = requests.post(BACKEND + "/upload", data=data, files=files, timeout=30)
                if response.status_code == 200 and response.json().get("status") == "ok":
                    self.status_lbl.config(text="Upload successful!")
                    self.show_receipt(items, costs)
                    self.reset()
                else:
                    raise Exception(f"Server error: {response.text}")
            except Exception as e:
                messagebox.showerror("Upload Error", str(e))
                self.status_lbl.config(text="Upload failed.")
            finally:
                self.bt_submit.config(state='normal')
                self.bt_start.config(state='normal')

        threading.Thread(target=do_upload, daemon=True).start()

    def show_receipt(self, items, costs):
        total = sum(costs)
        w, h = 400, 30 + 20 * (len(items) + 3)
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        y = 10
        draw.text((10, y), "Rolefy Receipt", font=font)
        y += 20
        draw.text((10, y), f"Buyer: {self.ebuyer.get()}, Seller: {self.eseller.get()}", font=font)
        y += 20
        for itm, c in zip(items, costs):
            draw.text((10, y), f"{itm}: €{c:.2f}", font=font)
            y += 20
        draw.text((10, y), f"Total: €{total:.2f}", font=font)

        path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")], title="Save Receipt As")
        if path:
            try:
                img.save(path)
                messagebox.showinfo("Saved", f"Receipt saved to {path}")
            except Exception as e:
                messagebox.showerror("Save Error", f"No se pudo guardar el recibo:\n{e}")

    def reset(self):
        self.audio_data = None
        self.bt_submit.config(state='disabled')
        self.tp.delete("1.0", "end")
        self.tc.delete("1.0", "end")
        self.status_lbl.config(text="Ready")
        self.timer_lbl.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
