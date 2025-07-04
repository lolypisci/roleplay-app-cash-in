# Código completo actualizado con:
# - Cabecera centrada con logo reducido, nombre app y nombre docente
# - Scroll automático al reducir ventana
# - Layout adaptativo y centrado
# - Corrección en sistema de grabación

import sounddevice as sd, numpy as np, wave, threading, tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, Canvas, Frame, Scrollbar
from PIL import Image, ImageDraw, ImageFont, ImageTk
import io, json, requests, os
from datetime import datetime
import subprocess

# Configuración remota
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"
ASSETS_DIR = "assets"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
HANDOUT_PATH = os.path.join("handouts", "handout.png")
RECEIPT_DIR = "receipts"
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

FONT_PRIMARY = os.path.join(FONTS_DIR, "Lexend-Regular.ttf")
FONT_TITLE = os.path.join(FONTS_DIR, "Jost-SemiBold.ttf")
FONT_FOOTER = os.path.join(FONTS_DIR, "Nunito-Regular.ttf")

os.makedirs(RECEIPT_DIR, exist_ok=True)

# Colores y estilo
COLOR_BG = "#FFFFFF"
COLOR_PRIMARY = "#A9E5BB"
COLOR_SECONDARY = "#89DCEB"
COLOR_ACCENT = "#1E90FF"
COLOR_TEXT = "#333333"
COLOR_MUTED = "#777777"
BUTTON_RADIUS = 20


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
        try:
            self.frames = []; self.recording = True

            def cb(indata, *_):
                if self.recording:
                    self.frames.append(indata.copy())

            self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=cb)
            self.stream.start()
        except Exception as e:
            self.recording = False
            print("Recording failed:", e)

    def stop(self):
        try:
            self.recording = False
            self.stream.stop(); self.stream.close()
            return np.concatenate(self.frames, axis=0) if self.frames else None
        except:
            return None


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
        root.title("ROLEFY – STUDENT")
        root.geometry("800x780")
        root.configure(bg=COLOR_BG)

        # Scrollable canvas
        canvas = Canvas(root, bg=COLOR_BG)
        scrollbar = Scrollbar(root, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        self.container = Frame(canvas, bg=COLOR_BG)
        self.container.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.container, anchor="n")

        # Cabecera: logo + título + teacher
        header = Frame(self.container, bg=COLOR_BG)
        header.pack(pady=10)

        if os.path.exists(LOGO_PATH):
            logo_img = Image.open(LOGO_PATH).resize((60, 60))
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            logo_lbl = tk.Label(header, image=self.logo_tk, bg=COLOR_BG)
            logo_lbl.pack(side="left", padx=10)

        text_frame = Frame(header, bg=COLOR_BG)
        text_frame.pack(side="left")
        tk.Label(text_frame, text="ROLEFY", font=("Jost", 20, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="w")
        tk.Label(text_frame, text="Teacher: María Dolores Rivas Sánchez", font=("Lexend", 10), bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w")

        # Campos de entrada
        self._add_entry("Buyer:", 1)
        self._add_entry("Seller:", 2)
        self._add_text("Items (1 per line):", 3)
        self._add_text("Costs (same count):", 4)

        self.button_frame = tk.Frame(self.container, bg=COLOR_BG)
        self.button_frame.pack(pady=15)
        self.bt_start = self._styled_button("Start Recording", COLOR_PRIMARY, self.start_recording)
        self.bt_start.pack(side="left", padx=10)

        self.bt_stop = self._styled_button("Stop Recording", "#FF6666", self.stop_recording)
        self.bt_stop.pack(side="left", padx=10)
        self.bt_stop['state'] = 'disabled'

        self.bt_submit = self._styled_button("Submit", COLOR_SECONDARY, self.submit)
        self.bt_submit.pack(side="left", padx=10)
        self.bt_submit['state'] = 'disabled'

        self.status_lbl = tk.Label(self.container, text="Ready", fg=COLOR_TEXT, bg=COLOR_BG, font=("Lexend", 10))
        self.status_lbl.pack()

        self.timer_lbl = tk.Label(self.container, text="00:00", fg="green", bg=COLOR_BG, font=("Lexend", 10))
        self.timer_lbl.pack()

        tk.Label(self.container, text="Handout Preview", bg=COLOR_BG, font=("Lexend", 10)).pack(pady=(15, 0))
        self.handout_canvas = tk.Label(self.container, bg=COLOR_BG)
        self.handout_canvas.pack()
        self.bt_open_handout = self._styled_button("Open Handout", COLOR_ACCENT, self.open_handout)
        self.bt_open_handout.pack(pady=10, anchor="center")

        tk.Label(self.container, text="© All rights reserved\nApp created by María Dolores Rivas Sánchez",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=("Nunito", 8)).pack(pady=(20, 10))

        self.recorder = Recorder()
        self.audio_data = None
        self.seconds = 0
        self.timer = None

        self.refresh_handout()

    def _styled_button(self, text, color, command):
        return tk.Button(self.button_frame, text=text, bg=color, fg="white", width=16, height=2,
                         font=("Jost", 10, "bold"), bd=0, relief="flat", command=command)

    def _add_entry(self, label, row):
        f = Frame(self.container, bg=COLOR_BG)
        f.pack(pady=5)
        tk.Label(f, text=label, bg=COLOR_BG, font=("Lexend", 10)).pack(side="left", padx=10)
        entry = tk.Entry(f, width=40, font=("Lexend", 10))
        entry.pack(side="left")
        setattr(self, f"e{label.split()[0].lower()}", entry)

    def _add_text(self, label, row):
        f = Frame(self.container, bg=COLOR_BG)
        f.pack(pady=5)
        tk.Label(f, text=label, bg=COLOR_BG, font=("Lexend", 10)).pack(anchor="w", padx=10)
        text = tk.Text(f, height=4, width=60, font=("Lexend", 10))
        text.pack()
        setattr(self, f"t{label.split()[0][0].lower()}", text)

    def refresh_handout(self):
        if os.path.exists(HANDOUT_PATH):
            img = Image.open(HANDOUT_PATH)
            img.thumbnail((600, 300))
            self.himg = ImageTk.PhotoImage(img)
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
                    # Aquí podrías llamar a self.show_receipt(items, costs) si usas recibos visuales
                else: raise Exception(r.text)
            except Exception as e:
                messagebox.showerror("Upload error", str(e))

        threading.Thread(target=upload).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
