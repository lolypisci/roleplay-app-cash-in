import sounddevice as sd, numpy as np, wave, threading, tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageDraw, ImageFont
import io, json, requests, os
from datetime import datetime
import subprocess

# Configuración remota
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"
ASSETS_DIR = "assets"
HANDOUT_PATH = os.path.join("handouts", "handout.png")
RECEIPT_DIR = "receipts"
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
FONT_PATH = os.path.join(ASSETS_DIR, "arial.ttf")  # opcional

os.makedirs(RECEIPT_DIR, exist_ok=True)

def get_backend_url():
    try:
        r = requests.get(CONFIG_URL, timeout=5)
        url = r.json().get("backend_url", "").rstrip("/")
        return url if url else DEFAULT_BACKEND
    except:
        root = tk.Tk(); root.withdraw()
        url = simpledialog.askstring("Backend URL", "Introduce la URL del backend:", initialvalue=DEFAULT_BACKEND)
        root.destroy()
        if not url: exit("No backend provided")
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
        self.recording = False
        self.stream.stop(); self.stream.close()
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
        root.geometry("800x700")

        # Estilo
        self.bg = "#f7f9fc"
        self.root.configure(bg=self.bg)

        # Campos
        self._add_entry("Buyer:", 0)
        self._add_entry("Seller:", 1)
        self._add_text("Items (1 per line):", 2)
        self._add_text("Costs (same count):", 3)

        # Botones
        self.button_frame = tk.Frame(root, bg=self.bg)
        self.button_frame.grid(row=4, column=0, columnspan=2, pady=10)

        self.bt_start = tk.Button(self.button_frame, text="Start Recording", bg="#4CAF50", fg="white",
                                  width=16, height=2, command=self.start_recording)
        self.bt_start.pack(side="left", padx=10)

        self.bt_stop = tk.Button(self.button_frame, text="Stop Recording", bg="#b22222", fg="white",
                                 width=16, height=2, state='disabled', command=self.stop_recording)
        self.bt_stop.pack(side="left", padx=10)

        self.bt_submit = tk.Button(self.button_frame, text="Submit", bg="#1E90FF", fg="white",
                                   width=16, height=2, state='disabled', command=self.submit)
        self.bt_submit.pack(side="left", padx=10)

        # Estado y tiempo
        self.status_lbl = tk.Label(root, text="Ready", fg="black", bg=self.bg, font=("Arial", 10))
        self.status_lbl.grid(row=5, column=0, columnspan=2, pady=(20, 0))
        self.timer_lbl = tk.Label(root, text="00:00", fg="green", bg=self.bg, font=("Arial", 10))
        self.timer_lbl.grid(row=6, column=0, columnspan=2)

        # Handout
        self.handout_label = tk.Label(root, text="Handout Preview", bg=self.bg, font=("Arial", 10))
        self.handout_label.grid(row=7, column=0, columnspan=2, pady=(20, 0))

        self.handout_canvas = tk.Label(root, bg=self.bg)
        self.handout_canvas.grid(row=8, column=0, columnspan=2)

        self.bt_open_handout = tk.Button(root, text="Open Handout", command=self.open_handout)
        self.bt_open_handout.grid(row=9, column=0, columnspan=2, pady=10)

        self.recorder = Recorder()
        self.audio_data = None
        self.seconds = 0
        self.timer = None

        self.refresh_handout()

    def _add_entry(self, label, row):
        tk.Label(self.root, text=label, bg=self.bg).grid(row=row, column=0, sticky="e", padx=10, pady=5)
        entry = tk.Entry(self.root, width=40)
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        setattr(self, f"e{label.split()[0].lower()}", entry)

    def _add_text(self, label, row):
        tk.Label(self.root, text=label, bg=self.bg).grid(row=row, column=0, sticky="ne", padx=10, pady=5)
        text = tk.Text(self.root, height=4, width=40)
        text.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        setattr(self, f"t{label.split()[0][0].lower()}", text)

    def refresh_handout(self):
        if os.path.exists(HANDOUT_PATH):
            img = Image.open(HANDOUT_PATH)
            img.thumbnail((600, 300))
            self.himg = tk.PhotoImage(img)
            self.handout_canvas.config(image=self.himg)
        else:
            self.handout_canvas.config(text="(No handout.png found in /handouts)")

    def open_handout(self):
        try:
            os.startfile(HANDOUT_PATH)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir el handout:\n{e}")

    def update_timer(self):
        self.seconds += 1
        m, s = divmod(self.seconds, 60)
        self.timer_lbl.config(text=f"{m:02}:{s:02}")
        self.timer = self.root.after(1000, self.update_timer)

    def start_recording(self):
        if not self.ebuyer.get().strip() or not self.eseller.get().strip():
            return messagebox.showwarning("Incomplete", "Buyer and Seller required.")
        self.bt_start['state'] = 'disabled'
        self.bt_stop['state'] = 'normal'
        self.bt_submit['state'] = 'disabled'
        self.status_lbl['text'] = "Recording..."
        self.audio_data = None
        self.seconds = 0
        self.update_timer()
        threading.Thread(target=self.recorder.start, daemon=True).start()

    def stop_recording(self):
        if self.timer: self.root.after_cancel(self.timer)
        self.bt_stop['state'] = 'disabled'
        self.bt_start['state'] = 'normal'
        self.bt_submit['state'] = 'normal'
        self.status_lbl['text'] = "Stopped"
        self.audio_data = self.recorder.stop()

    def submit(self):
        items = [i.strip() for i in self.ti.get("1.0", "end").splitlines() if i.strip()]
        costs = [c.strip().replace(",", ".") for c in self.tc.get("1.0", "end").splitlines() if c.strip()]
        if len(items) != len(costs): return messagebox.showwarning("Error", "Mismatch in items and costs")
        try: costs = [float(c) for c in costs]
        except: return messagebox.showwarning("Error", "Invalid cost format")
        if self.audio_data is None: return messagebox.showwarning("Error", "No audio")
        wav = encode_wav(self.audio_data)
        files = {"audio": ("r.wav", wav, "audio/wav")}
        data = {
            "comprador": self.ebuyer.get(), "vendedor": self.eseller.get(),
            "productos": json.dumps(items), "costes": json.dumps(costs)
        }
        def upload():
            try:
                r = requests.post(BACKEND + "/upload", data=data, files=files)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    self.status_lbl['text'] = "Uploaded!"
                    self.show_receipt(items, costs)
                else: raise Exception(r.text)
            except Exception as e:
                messagebox.showerror("Upload error", str(e))
        threading.Thread(target=upload).start()

    def show_receipt(self, items, costs):
        total = sum(costs)
        img = Image.new("RGB", (595, 842), "white")  # A4
        draw = ImageDraw.Draw(img)
        try: font = ImageFont.truetype(FONT_PATH, 16)
        except: font = ImageFont.load_default()
        y = 60
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).resize((150, 150))
            img.paste(logo, (220, 10))
            y += 80
        draw.text((50, y), f"Buyer: {self.ebuyer.get()}    Seller: {self.eseller.get()}", font=font); y += 30
        for i, c in zip(items, costs):
            draw.text((50, y), f"{i}: €{c:.2f}", font=font); y += 25
        draw.text((50, y), f"Total: €{total:.2f}", font=font); y += 40
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((50, 800), "This receipt confirms successful submission.", font=font)
        draw.text((350, 800), f"Rolefy · {now}", font=font)

        filename = os.path.join(RECEIPT_DIR, f"{self.ebuyer.get()}_{now.replace(':','-')}.png")
        img.save(filename)
        os.startfile(filename)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
