import sounddevice as sd, numpy as np, wave, threading, tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
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
        root.title("ROLEFY – STUDENT")
        root.geometry("800x780")
        root.configure(bg=COLOR_BG)

        # Logo
        if os.path.exists(LOGO_PATH):
            logo_img = Image.open(LOGO_PATH).resize((120, 120))
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            tk.Label(root, image=self.logo_tk, bg=COLOR_BG).grid(row=0, column=0, columnspan=2, pady=(10, 0))
        
        # Campos
        self._add_entry("Buyer:", 1)
        self._add_entry("Seller:", 2)
        self._add_text("Items (1 per line):", 3)
        self._add_text("Costs (same count):", 4)

        # Botones
        self.button_frame = tk.Frame(root, bg=COLOR_BG)
        self.button_frame.grid(row=5, column=0, columnspan=2, pady=15)

        self.bt_start = self._styled_button("Start Recording", COLOR_PRIMARY, self.start_recording)
        self.bt_start.pack(side="left", padx=10)

        self.bt_stop = self._styled_button("Stop Recording", "#FF6666", self.stop_recording)
        self.bt_stop.pack(side="left", padx=10)
        self.bt_stop['state'] = 'disabled'

        self.bt_submit = self._styled_button("Submit", COLOR_SECONDARY, self.submit)
        self.bt_submit.pack(side="left", padx=10)
        self.bt_submit['state'] = 'disabled'

        # Estado y tiempo
        self.status_lbl = tk.Label(root, text="Ready", fg=COLOR_TEXT, bg=COLOR_BG, font=("Lexend", 10))
        self.status_lbl.grid(row=6, column=0, columnspan=2, pady=(10, 0))

        self.timer_lbl = tk.Label(root, text="00:00", fg="green", bg=COLOR_BG, font=("Lexend", 10))
        self.timer_lbl.grid(row=7, column=0, columnspan=2)

        # Handout
        tk.Label(root, text="Handout Preview", bg=COLOR_BG, font=("Lexend", 10)).grid(row=8, column=0, columnspan=2, pady=(15, 0))
        self.handout_canvas = tk.Label(root, bg=COLOR_BG)
        self.handout_canvas.grid(row=9, column=0, columnspan=2)

        self.bt_open_handout = self._styled_button("Open Handout", COLOR_ACCENT, self.open_handout)
        self.bt_open_handout.grid(row=10, column=0, columnspan=2, pady=10)

        # Footer
        tk.Label(root, text="© All rights reserved\nApp created by María Dolores Rivas Sánchez",
                 bg=COLOR_BG, fg=COLOR_MUTED, font=("Nunito", 8)).grid(row=11, column=0, columnspan=2, pady=(20, 10))

        self.recorder = Recorder()
        self.audio_data = None
        self.seconds = 0
        self.timer = None

        self.refresh_handout()

    def _styled_button(self, text, color, command):
        return tk.Button(self.button_frame, text=text, bg=color, fg="white", width=16, height=2,
                         font=("Jost", 10, "bold"), bd=0, relief="flat", command=command)

    def _add_entry(self, label, row):
        tk.Label(self.root, text=label, bg=COLOR_BG, font=("Lexend", 10)).grid(row=row, column=0, sticky="e", padx=10, pady=5)
        entry = tk.Entry(self.root, width=40, font=("Lexend", 10))
        entry.grid(row=row, column=1, sticky="w", padx=10, pady=5)
        setattr(self, f"e{label.split()[0].lower()}", entry)

    def _add_text(self, label, row):
        tk.Label(self.root, text=label, bg=COLOR_BG, font=("Lexend", 10)).grid(row=row, column=0, sticky="ne", padx=10, pady=5)
        text = tk.Text(self.root, height=4, width=40, font=("Lexend", 10))
        text.grid(row=row, column=1, sticky="w", padx=10, pady=5)
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
                    self.show_receipt(items, costs)
                else: raise Exception(r.text)
            except Exception as e:
                messagebox.showerror("Upload error", str(e))

        threading.Thread(target=upload).start()

    def show_receipt(self, items, costs):
        total = sum(costs)
        img = Image.new("RGB", (595, 842), "white")  # A4
        draw = ImageDraw.Draw(img)

        try:
            font_main = ImageFont.truetype(FONT_PRIMARY, 16)
            font_footer = ImageFont.truetype(FONT_FOOTER, 10)
            font_title = ImageFont.truetype(FONT_TITLE, 24)
        except:
            font_main = ImageFont.load_default()
            font_footer = font_main
            font_title = font_main

        y = 40
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).resize((100, 100))
            img.paste(logo, (245, y))
            y += 120

        draw.text((170, y), "ROLEFY", font=font_title, fill=COLOR_PRIMARY); y += 40
        draw.text((50, y), f"Buyer: {self.ebuyer.get()}    Seller: {self.eseller.get()}", font=font_main, fill=COLOR_TEXT); y += 30

        for i, c in zip(items, costs):
            draw.text((50, y), f"{i}: €{c:.2f}", font=font_main, fill=COLOR_TEXT); y += 25

        draw.text((50, y), f"Total: €{total:.2f}", font=font_main, fill=COLOR_TEXT); y += 40
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        draw.text((50, 800), "Teacher: María Dolores Rivas Sánchez", font=font_footer, fill=COLOR_MUTED)
        draw.text((370, 800), f"ROLEFY · {now}", font=font_footer, fill=COLOR_MUTED)

        filename = os.path.join(RECEIPT_DIR, f"{self.ebuyer.get()}_{now.replace(':','-')}.png")
        img.save(filename)
        os.startfile(filename)


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
