import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, Canvas, Frame, Scrollbar
from PIL import Image, ImageTk
import io
import json
import requests
import os

# Configuración
CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"
ASSETS_DIR = "assets"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
HANDOUT_PATH = os.path.join("handouts", "handout.png")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")

SAMPLE_RATE = 44100
CHANNELS = 1

COLOR_BG = "#FFFFFF"
COLOR_PRIMARY = "#A9E5BB"       # verde menta
COLOR_SECONDARY = "#89DCEB"     # azul turquesa claro
COLOR_ACCENT = "#1E90FF"        # azul vivo
COLOR_TEXT = "#333333"
COLOR_MUTED = "#777777"


def get_backend_url():
    try:
        r = requests.get(CONFIG_URL, timeout=5)
        url = r.json().get("backend_url", "").rstrip("/")
        return url if url else DEFAULT_BACKEND
    except:
        root = tk.Tk()
        root.withdraw()
        url = simpledialog.askstring("Backend URL", "Introduce la URL del backend:", initialvalue=DEFAULT_BACKEND)
        root.destroy()
        if not url:
            exit("No backend provided")
        return url.rstrip("/")


BACKEND = get_backend_url()


class Recorder:
    def __init__(self):
        self.recording = False
        self.frames = []

    def start(self):
        try:
            self.frames = []
            self.recording = True

            def callback(indata, frames, time, status):
                if self.recording:
                    self.frames.append(indata.copy())

            self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, callback=callback)
            self.stream.start()
        except Exception as e:
            self.recording = False
            messagebox.showerror("Error", f"No se pudo iniciar la grabación:\n{e}")

    def stop(self):
        try:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            return np.concatenate(self.frames, axis=0) if self.frames else None
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo detener la grabación:\n{e}")
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
        root.title("ROLEFY – STUDENT")
        root.geometry("900x800")
        root.configure(bg=COLOR_BG)

        self.canvas = Canvas(root, bg=COLOR_BG, highlightthickness=0)
        self.scrollbar = Scrollbar(root, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.container = Frame(self.canvas, bg=COLOR_BG)
        self.window = self.canvas.create_window((0, 0), window=self.container, anchor="n")

        self.container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self.build_ui()
        self.recorder = Recorder()
        self.audio_data = None
        self.seconds = 0
        self.timer = None

    def build_ui(self):
        # Cabecera con logo y textos
        header = Frame(self.container, bg=COLOR_BG)
        header.pack(pady=10)

        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image.open(LOGO_PATH)
                logo_img = logo_img.resize((50, 50), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_img)
                logo_lbl = tk.Label(header, image=self.logo_tk, bg=COLOR_BG)
                logo_lbl.pack(side="left", padx=10)
            except:
                logo_lbl = tk.Label(header, text="ROLEFY", font=("Arial", 24), bg=COLOR_BG)
                logo_lbl.pack(side="left")

        text_frame = Frame(header, bg=COLOR_BG)
        text_frame.pack(side="left")

        tk.Label(text_frame, text="ROLEFY", font=("Jost", 20, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="w")
        tk.Label(text_frame, text="Teacher: María Dolores Rivas Sánchez", font=("Lexend", 10), bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w")

        # Entradas Buyer y Seller
        self.ebuyer = self._add_entry("Buyer:")
        self.eseller = self._add_entry("Seller:")

        # Textos Items y Costs
        self._add_text("Items (1 per line):")
        self._add_text("Costs (same count):")

        # Handout (imagen preview proporcional)
        if os.path.exists(HANDOUT_PATH):
            try:
                handout_img = Image.open(HANDOUT_PATH)
                handout_img.thumbnail((500, 9999), Image.Resampling.LANCZOS)  # ancho máximo 500px, altura proporcional
                self.handout_tk = ImageTk.PhotoImage(handout_img)
                handout_lbl = tk.Label(self.container, image=self.handout_tk, bg=COLOR_BG)
                handout_lbl.pack(pady=10)
            except:
                pass

        # Botón Open Handout
        self.bt_open_handout = tk.Button(self.container, text="Open Handout", command=self.open_handout,
                                         bg=COLOR_ACCENT, fg="white", relief="flat")
        self.bt_open_handout.pack(pady=10)

        # Botones Start, Stop, Submit
        btn_frame = Frame(self.container, bg=COLOR_BG)
        btn_frame.pack(pady=15)
        self.bt_start = self._styled_button("Start Recording", COLOR_PRIMARY, self.start_recording, btn_frame)
        self.bt_stop = self._styled_button("Stop Recording", "#FF6666", self.stop_recording, btn_frame)
        self.bt_submit = self._styled_button("Submit", COLOR_SECONDARY, self.submit, btn_frame)
        self.bt_stop["state"] = "disabled"
        self.bt_submit["state"] = "disabled"

        # Etiquetas estado y temporizador
        self.status_lbl = tk.Label(self.container, text="Ready", bg=COLOR_BG, fg=COLOR_TEXT)
        self.status_lbl.pack()
        self.timer_lbl = tk.Label(self.container, text="00:00", bg=COLOR_BG, fg="green")
        self.timer_lbl.pack()

        # Pie de página copyright con dos líneas
        footer_frame = tk.Frame(self.container, bg=COLOR_BG)
        footer_frame.pack(pady=20)

        tk.Label(footer_frame,
                 text="© All Rights Reserved.",
                 font=("Lexend", 9),
                 bg=COLOR_BG,
                 fg=COLOR_MUTED).pack()

        tk.Label(footer_frame,
                 text="Upgraded by María Dolores Rivas Sánchez",
                 font=("Lexend", 9),
                 bg=COLOR_BG,
                 fg=COLOR_MUTED).pack()

    def open_handout(self):
        if os.path.exists(HANDOUT_PATH):
            os.startfile(HANDOUT_PATH)

    def _add_entry(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5)
        tk.Label(frame, text=label_text, bg=COLOR_BG).pack(side="left", padx=10)
        entry = tk.Entry(frame, width=40, relief="solid", bd=1)
        entry.pack(side="left")
        return entry

    def _add_text(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5)
        tk.Label(frame, text=label_text, bg=COLOR_BG).pack(anchor="w", padx=10)
        text = tk.Text(frame, height=4, width=60, relief="solid", bd=1)
        text.pack()
        setattr(self, f"t{label_text.split()[0][0].lower()}", text)

    def _styled_button(self, text, color, command, parent):
        btn = tk.Button(parent, text=text, bg=color, fg="white", width=16, height=2, bd=0, command=command)
        btn.pack(side="left", padx=10)
        return btn

    def start_recording(self):
        if not self.ebuyer.get().strip() or not self.eseller.get().strip():
            return messagebox.showwarning("Campos incompletos", "Buyer y Seller son obligatorios.")
        self.bt_start["state"] = "disabled"
        self.bt_stop["state"] = "normal"
        self.bt_submit["state"] = "disabled"
        self.status_lbl["text"] = "Recording..."
        self.audio_data = None
        self.seconds = 0
        self.update_timer()
        threading.Thread(target=self.recorder.start, daemon=True).start()

    def stop_recording(self):
        if self.timer:
            self.root.after_cancel(self.timer)
        self.bt_stop["state"] = "disabled"
        self.bt_start["state"] = "normal"
        self.bt_submit["state"] = "normal"
        self.status_lbl["text"] = "Stopped"
        self.audio_data = self.recorder.stop()

    def submit(self):
        items = [i.strip() for i in self.ti.get("1.0", "end").splitlines() if i.strip()]
        costs = [c.strip().replace(",", ".") for c in self.tc.get("1.0", "end").splitlines() if c.strip()]
        if len(items) != len(costs):
            return messagebox.showwarning("Error", "Los números de productos y precios no coinciden.")
        try:
            costs = [float(c) for c in costs]
        except:
            return messagebox.showwarning("Error", "Formato de coste inválido.")
        if self.audio_data is None:
            return messagebox.showwarning("Error", "No se grabó audio.")

        wav = encode_wav(self.audio_data)
        files = {"audio": ("recording.wav", wav, "audio/wav")}
        data = {
            "comprador": self.ebuyer.get(),
            "vendedor": self.eseller.get(),
            "productos": json.dumps(items),
            "costes": json.dumps(costs),
        }

        def upload():
            try:
                r = requests.post(BACKEND + "/upload", data=data, files=files)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    self.status_lbl["text"] = "Uploaded!"
                else:
                    raise Exception(r.text)
            except Exception as e:
                messagebox.showerror("Upload error", str(e))

        threading.Thread(target=upload).start()

    def update_timer(self):
        self.seconds += 1
        m, s = divmod(self.seconds, 60)
        self.timer_lbl.config(text=f"{m:02}:{s:02}")
        self.timer = self.root.after(1000, self.update_timer)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        # Limitar scroll superior para que no sobrepase cabecera
        if self.canvas.yview()[0] < 0:
            self.canvas.yview_moveto(0)

    def on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.window, width=canvas_width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
