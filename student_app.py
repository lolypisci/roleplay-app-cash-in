import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
from tkinter import filedialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import io
import json
import requests
from datetime import datetime
import os
import sys
import subprocess

# Config
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"  # fallback local URL
LOGO_PATH = os.path.join("static", "logo.png")

def get_backend_url():
    try:
        data = requests.get(CONFIG_URL, timeout=5).json()
        url = data.get("backend_url", "").rstrip("/")
        if url:
            return url
        else:
            raise ValueError("Empty backend_url in config")
    except Exception:
        root = tk.Tk()
        root.withdraw()
        url = simpledialog.askstring("Backend URL", "No se pudo obtener la URL del backend.\nIntroduce la URL del backend Rolefy:", initialvalue=DEFAULT_BACKEND)
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
        root.configure(bg="#f0f4f8")
        root.geometry("420x480")
        root.resizable(False, False)

        # Logo arriba centrado
        self.logo_img = None
        if os.path.isfile(LOGO_PATH):
            try:
                logo_raw = Image.open(LOGO_PATH)
                logo_raw = logo_raw.resize((120, 60), Image.ANTIALIAS)
                self.logo_img = ImageTk.PhotoImage(logo_raw)
                logo_label = tk.Label(root, image=self.logo_img, bg="#f0f4f8")
                logo_label.grid(row=0, column=0, columnspan=2, pady=(10, 20))
            except Exception as e:
                print("No se pudo cargar logo:", e)

        # Estilos comunes
        label_style = {"bg": "#f0f4f8", "font": ("Segoe UI", 11, "bold"), "anchor": "w"}
        entry_style = {"font": ("Segoe UI", 11), "bd": 2, "relief": "groove"}
        text_style = {"font": ("Segoe UI", 11), "bd": 2, "relief": "groove"}

        # Buyer
        tk.Label(root, text="Buyer:", **label_style).grid(row=1, column=0, sticky="w", padx=20)
        self.ebuyer = tk.Entry(root, width=30, **entry_style)
        self.ebuyer.grid(row=1, column=1, padx=20, pady=5)

        # Seller
        tk.Label(root, text="Seller:", **label_style).grid(row=2, column=0, sticky="w", padx=20)
        self.eseller = tk.Entry(root, width=30, **entry_style)
        self.eseller.grid(row=2, column=1, padx=20, pady=5)

        # Items
        tk.Label(root, text="Items (one per line):", **label_style).grid(row=3, column=0, sticky="nw", padx=20)
        self.tp = tk.Text(root, height=6, width=30, **text_style)
        self.tp.grid(row=3, column=1, padx=20, pady=5)

        # Costs
        tk.Label(root, text="Costs (one per line):", **label_style).grid(row=4, column=0, sticky="nw", padx=20)
        self.tc = tk.Text(root, height=6, width=30, **text_style)
        self.tc.grid(row=4, column=1, padx=20, pady=5)

        # Botones con colores y hover (básico)
        self.bt_start = tk.Button(root, text="Start Recording", command=self.start_recording, bg="#4CAF50", fg="white", activebackground="#45a049", font=("Segoe UI", 12, "bold"), relief="flat")
        self.bt_start.grid(row=5, column=0, pady=15, padx=20, sticky="ew")

        self.bt_stop = tk.Button(root, text="Stop Recording", command=self.stop_recording, state='disabled', bg="#f44336", fg="white", activebackground="#da190b", font=("Segoe UI", 12, "bold"), relief="flat")
        self.bt_stop.grid(row=5, column=1, pady=15, padx=20, sticky="ew")

        self.bt_submit = tk.Button(root, text="Submit", command=self.submit, state='disabled', bg="#2196F3", fg="white", activebackground="#0b7dda", font=("Segoe UI", 12, "bold"), relief="flat")
        self.bt_submit.grid(row=6, column=0, columnspan=2, pady=10, padx=50, sticky="ew")

        # Status label
        self.status_lbl = tk.Label(root, text="", fg="#333", bg="#f0f4f8", font=("Segoe UI", 10, "italic"))
        self.status_lbl.grid(row=7, column=0, columnspan=2)

        # Timer label
        self.timer_lbl = tk.Label(root, text="", fg="#666", bg="#f0f4f8", font=("Segoe UI", 10))
        self.timer_lbl.grid(row=8, column=0, columnspan=2)

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
        self.status_lbl.config(text="Recording...", fg="#4CAF50")
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
            self.status_lbl.config(text="", fg="#333")
            self.bt_start.config(state='normal')
            self.bt_stop.config(state='disabled')
            return
        self.audio_data = data
        self.status_lbl.config(text="Recording stopped.", fg="#2196F3")
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

        self.status_lbl.config(text="Uploading...", fg="#2196F3")
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
                    self.status_lbl.config(text="Upload successful!", fg="#4CAF50")
                    self.show_receipt(items, costs)
                    self.reset()
                else:
                    raise Exception(f"Server error: {response.text}")
            except Exception as e:
                messagebox.showerror("Upload Error", str(e))
                self.status_lbl.config(text="Upload failed.", fg="#f44336")
            finally:
                self.bt_submit.config(state='normal')
                self.bt_start.config(state='normal')

        threading.Thread(target=do_upload, daemon=True).start()

    def show_receipt(self, items, costs):
        total = sum(costs)
        w, h = 450, 50 + 30 * (len(items) + 4)
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)

        # Fuente elegante y tamaño
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 22)
            font_subtitle = ImageFont.truetype("arial.ttf", 14)
            font_regular = ImageFont.truetype("arial.ttf", 16)
        except:
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
            font_regular = ImageFont.load_default()

        # Color principal
        main_color = (33, 150, 243)  # azul intenso

        # Logo (si existe)
        if os.path.isfile(LOGO_PATH):
            try:
                logo = Image.open(LOGO_PATH)
                logo.thumbnail((80, 40), Image.ANTIALIAS)
                img.paste(logo, (15, 10), logo.convert("RGBA"))
            except Exception as e:
                print("No se pudo pegar logo en recibo:", e)

        x_text_start = 110
        y = 15

        draw.text((x_text_start, y), "Rolefy Receipt", font=font_title, fill=main_color)
        y += 35
        draw.text((x_text_start, y), f"Buyer: {self.ebuyer.get()}", font=font_subtitle, fill=(0,0,0))
        y += 25
        draw.text((x_text_start, y), f"Seller: {self.eseller.get()}", font=font_subtitle, fill=(0,0,0))
        y += 25
        draw.line((15, y, w - 15, y), fill=main_color, width=2)
        y += 10

        for itm, c in zip(items, costs):
            draw.text((20, y), itm, font=font_regular, fill=(0,0,0))
            draw.text((w - 120, y), f"€{c:.2f}", font=font_regular, fill=(0,0,0))
            y += 30

        draw.line((15, y, w - 15, y), fill=main_color, width=2)
        y += 10

        draw.text((20, y), "Total:", font=font_subtitle, fill=(0,0,0))
        draw.text((w - 120, y), f"€{total:.2f}", font=font_subtitle, fill=(0,0,0))

        # Carpeta y guardado automático
        folder = "Receipts"
        os.makedirs(folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"receipt_{timestamp}.png"
        path = os.path.join(folder, filename)

        try:
            img.save(path)
        except Exception as e:
            messagebox.showerror("Save Error", f"No se pudo guardar el recibo:\n{e}")
            return

        # Abrir archivo automáticamente
        try:
            if sys.platform.startswith('darwin'):
                subprocess.call(('open', path))
            elif sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform.startswith('linux'):
                subprocess.call(('xdg-open', path))
        except Exception as e:
            messagebox.showwarning("Aviso", f"No se pudo abrir el archivo automáticamente:\n{e}")

        messagebox.showinfo("Guardado", f"Recibo guardado en:\n{os.path.abspath(path)}")

    def reset(self):
        self.audio_data = None
        self.bt_submit.config(state='disabled')
        self.tp.delete("1.0", "end")
        self.tc.delete("1.0", "end")
        self.status_lbl.config(text="Ready", fg="#333")
        self.timer_lbl.config(text="")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
