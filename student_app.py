import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageFont, ImageTk
import io, os, json, requests
from datetime import datetime

CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"
HANDOUT_PATH = "handouts/handout.png"
LOGO_PATH = "static/logo.png"
RECEIPTS_FOLDER = "receipts"

def get_backend_url():
    try:
        data = requests.get(CONFIG_URL, timeout=5).json()
        url = data.get("backend_url", "").rstrip("/")
        if url: return url
        raise ValueError("Empty backend_url")
    except:
        root = tk.Tk(); root.withdraw()
        url = simpledialog.askstring("Backend URL", "No se pudo obtener la URL del backend.\nIntroduce la URL:", initialvalue=DEFAULT_BACKEND)
        root.destroy()
        if not url: exit("No URL")
        return url.rstrip("/")

BACKEND = get_backend_url()
SAMPLE_RATE, CHANNELS = 44100, 1

class Recorder:
    def __init__(self):
        self.recording = False; self.frames = []
    def start(self):
        self.frames = []; self.recording = True
        def cb(indata, *_): 
            if self.recording: self.frames.append(indata.copy())
        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=cb)
        self.stream.start()
    def stop(self):
        self.recording = False; self.stream.stop(); self.stream.close()
        return np.concatenate(self.frames, axis=0) if self.frames else None

def encode_wav(data):
    raw = (np.int16(np.clip(data, -1, 1) * 32767)).tobytes()
    buf = io.BytesIO()
    wf = wave.open(buf, 'wb')
    wf.setnchannels(CHANNELS); wf.setsampwidth(2); wf.setframerate(SAMPLE_RATE)
    wf.writeframes(raw); wf.close()
    return buf.getvalue()

class App:
    def __init__(self, root):
        self.root = root
        root.title("Rolefy – Student")
        root.configure(bg="#f4f4f4")
        os.makedirs(RECEIPTS_FOLDER, exist_ok=True)

        self.audio_data = None
        self.recorder = Recorder()
        self.timer_seconds = 0
        self.timer_job = None

        frm = tk.Frame(root, bg="#f4f4f4")
        frm.pack(padx=20, pady=10)

        tk.Label(frm, text="Buyer:", bg="#f4f4f4").grid(row=0, column=0, sticky="e")
        self.ebuyer = tk.Entry(frm, width=30); self.ebuyer.grid(row=0, column=1)

        tk.Label(frm, text="Seller:", bg="#f4f4f4").grid(row=1, column=0, sticky="e")
        self.eseller = tk.Entry(frm, width=30); self.eseller.grid(row=1, column=1)

        tk.Label(frm, text="Items (one per line):", bg="#f4f4f4").grid(row=2, column=0, sticky="ne")
        self.tp = tk.Text(frm, height=5, width=30); self.tp.grid(row=2, column=1)

        tk.Label(frm, text="Costs (one per line):", bg="#f4f4f4").grid(row=3, column=0, sticky="ne")
        self.tc = tk.Text(frm, height=5, width=30); self.tc.grid(row=3, column=1)

        self.bt_start = tk.Button(frm, text="Start Recording", bg="#cc4444", fg="white", command=self.start_recording)
        self.bt_start.grid(row=4, column=0, pady=10)

        self.bt_stop = tk.Button(frm, text="Stop Recording", bg="#992222", fg="white", command=self.stop_recording, state="disabled")
        self.bt_stop.grid(row=4, column=1, pady=10)

        self.bt_submit = tk.Button(frm, text="Submit", bg="#4466cc", fg="white", command=self.submit, state="disabled")
        self.bt_submit.grid(row=5, column=0, columnspan=2, pady=5)

        self.status_lbl = tk.Label(frm, text="", fg="green", bg="#f4f4f4")
        self.status_lbl.grid(row=6, column=0, columnspan=2)

        self.timer_lbl = tk.Label(frm, text="00:00", font=("Arial", 14), bg="#f4f4f4", fg="black")
        self.timer_lbl.grid(row=7, column=0, columnspan=2, pady=5)

        # Handout visual
        self.handout_frame = tk.Frame(root, bg="#f4f4f4")
        self.handout_frame.pack(pady=5)
        self.handout_lbl = tk.Label(self.handout_frame, bg="#f4f4f4")
        self.handout_lbl.pack()
        self.load_handout()

    def load_handout(self):
        if os.path.exists(HANDOUT_PATH):
            try:
                img = Image.open(HANDOUT_PATH)
                img = img.resize((300, 200), Image.LANCZOS)
                self.handout_img = ImageTk.PhotoImage(img)
                self.handout_lbl.configure(image=self.handout_img)
            except:
                self.handout_lbl.configure(text="Error al cargar handout")
        else:
            self.handout_lbl.configure(text="No handout found")

    def start_recording(self):
        if not self.ebuyer.get().strip() or not self.eseller.get().strip():
            messagebox.showwarning("Datos requeridos", "Introduce los nombres de Buyer y Seller.")
            return
        self.audio_data = None
        self.status_lbl.config(text="Recording...", fg="green")
        self.bt_start.config(state="disabled")
        self.bt_stop.config(state="normal")
        self.bt_submit.config(state="disabled")
        self.timer_seconds = 0
        self.timer_lbl.config(text="00:00")
        self.recorder.start()
        self.update_timer()

    def update_timer(self):
        mins, secs = divmod(self.timer_seconds, 60)
        self.timer_lbl.config(text=f"{mins:02d}:{secs:02d}")
        self.timer_seconds += 1
        self.timer_job = self.root.after(1000, self.update_timer)

    def stop_recording(self):
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        self.audio_data = self.recorder.stop()
        if self.audio_data is None:
            messagebox.showwarning("No Audio", "No se detectó audio grabado.")
            self.status_lbl.config(text="")
            return
        self.status_lbl.config(text="Stopped", fg="red")
        self.bt_start.config(state="normal")
        self.bt_stop.config(state="disabled")
        self.bt_submit.config(state="normal")

    def submit(self):
        items = [line.strip() for line in self.tp.get("1.0", "end").splitlines() if line.strip()]
        costs_text = [line.strip() for line in self.tc.get("1.0", "end").splitlines() if line.strip()]
        if len(items) != len(costs_text):
            return messagebox.showwarning("Error", "Los items y costes no coinciden.")
        try:
            costs = [float(c.replace(",", ".")) for c in costs_text]
        except ValueError:
            return messagebox.showwarning("Error", "Costes inválidos.")

        if self.audio_data is None or self.audio_data.size == 0:
            return messagebox.showwarning("Error", "No hay audio grabado.")

        wav = encode_wav(self.audio_data)
        files = {"audio": ("recording.wav", wav, "audio/wav")}
        data = {
            "comprador": self.ebuyer.get().strip(),
            "vendedor": self.eseller.get().strip(),
            "productos": json.dumps(items),
            "costes": json.dumps(costs),
        }

        self.status_lbl.config(text="Uploading...", fg="blue")
        self.bt_submit.config(state="disabled")

        def upload():
            try:
                r = requests.post(BACKEND + "/upload", data=data, files=files, timeout=30)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    self.status_lbl.config(text="Uploaded!", fg="green")
                    self.save_receipt(items, costs)
                    self.reset()
                else:
                    raise Exception(r.text)
            except Exception as e:
                self.status_lbl.config(text="Upload failed", fg="red")
                messagebox.showerror("Error", str(e))
        threading.Thread(target=upload, daemon=True).start()

    def save_receipt(self, items, costs):
        total = sum(costs)
        w, h = 400, 100 + 20 * len(items)
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        try:
            logo = Image.open(LOGO_PATH).resize((80, 80))
            img.paste(logo, (10, 10))
        except:
            pass
        font = ImageFont.load_default()
        y = 10 if not os.path.exists(LOGO_PATH) else 100
        draw.text((10, y), f"Buyer: {self.ebuyer.get()}, Seller: {self.eseller.get()}", font=font); y += 20
        for itm, c in zip(items, costs):
            draw.text((10, y), f"{itm}: €{c:.2f}", font=font); y += 20
        draw.text((10, y), f"Total: €{total:.2f}", font=font)
        now = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(RECEIPTS_FOLDER, f"receipt_{now}.png")
        img.save(path)
        os.startfile(path)

    def reset(self):
        self.audio_data = None
        self.bt_submit.config(state="disabled")
        self.tp.delete("1.0", "end")
        self.tc.delete("1.0", "end")
        self.timer_lbl.config(text="00:00")
        self.status_lbl.config(text="Ready", fg="black")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
