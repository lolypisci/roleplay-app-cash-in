import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, Canvas, Frame, Scrollbar
from PIL import Image, ImageTk, ImageOps
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

FONT_PRIMARY = os.path.join(FONTS_DIR, "Lexend-Regular.ttf")
FONT_TITLE = os.path.join(FONTS_DIR, "Jost-SemiBold.ttf")
FONT_FOOTER = os.path.join(FONTS_DIR, "Nunito-Regular.ttf")

COLOR_BG = "#FFFFFF"
COLOR_PRIMARY = "#A9E5BB"
COLOR_SECONDARY = "#89DCEB"
COLOR_ACCENT = "#1E90FF"
COLOR_TEXT = "#333333"
COLOR_MUTED = "#777777"

SAMPLE_RATE = 44100
CHANNELS = 1

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
            if self.frames:
                return np.concatenate(self.frames, axis=0)
            else:
                return None
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
        root.geometry("800x780")
        root.configure(bg=COLOR_BG)

        # Scrollable canvas setup
        self.canvas = Canvas(root, bg=COLOR_BG)
        self.scrollbar = Scrollbar(root, command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.container = Frame(self.canvas, bg=COLOR_BG)
        self.window = self.canvas.create_window((0, 0), window=self.container, anchor="n")

        self.container.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)

        # Enable mousewheel scrolling on canvas
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # For Linux scroll up
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # For Linux scroll down

        # Cabecera
        header = Frame(self.container, bg=COLOR_BG)
        header.pack(pady=10)

        if os.path.exists(LOGO_PATH):
            logo_img = Image.open(LOGO_PATH).resize((60, 60), Image.ANTIALIAS)
            self.logo_tk = ImageTk.PhotoImage(logo_img)
            logo_lbl = tk.Label(header, image=self.logo_tk, bg=COLOR_BG)
            logo_lbl.pack(side="left", padx=10)

        text_frame = Frame(header, bg=COLOR_BG)
        text_frame.pack(side="left")

        tk.Label(text_frame, text="ROLEFY", font=("Jost", 20, "bold"), bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="w")
        tk.Label(text_frame, text="Teacher: María Dolores Rivas Sánchez", font=("Lexend", 10), bg=COLOR_BG, fg=COLOR_MUTED).pack(anchor="w", pady=(2,0))

        # Entradas formulario
        self._add_entry("Buyer:")
        self._add_entry("Seller:")
        self._add_text("Items (1 per line):")
        self._add_text("Costs (same count):")

        # Botones
        self.button_frame = Frame(self.container, bg=COLOR_BG)
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

        # Handout preview
        tk.Label(self.container, text="Handout Preview", bg=COLOR_BG, font=("Lexend", 10)).pack(pady=(15, 0))
        self.handout_canvas = tk.Label(self.container, bg=COLOR_BG)
        self.handout_canvas.pack()
        self.bt_open_handout = self._styled_button("Open Handout", COLOR_ACCENT, self.open_handout)
        self.bt_open_handout.pack(pady=10, anchor="center")

        # Footer
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

    def _add_entry(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5)
        tk.Label(frame, text=label_text, bg=COLOR_BG, font=("Lexend", 10)).pack(side="left", padx=10)
        entry = tk.Entry(frame, width=40, font=("Lexend", 10), relief="solid", bd=1, highlightthickness=0)
        entry.pack(side="left")
        setattr(self, f"e{label_text.split()[0].lower()}", entry)

    def _add_text(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5)
        tk.Label(frame, text=label_text, bg=COLOR_BG, font=("Lexend", 10)).pack(anchor="w", padx=10)
        text = tk.Text(frame, height=4, width=60, font=("Lexend", 10), relief="solid", bd=1, highlightthickness=0)
        text.pack()
        setattr(self, f"t{label_text.split()[0][0].lower()}", text)

    def refresh_handout(self):
        if os.path.exists(HANDOUT_PATH):
            img = Image.open(HANDOUT_PATH)
            img.thumbnail((600, 300), Image.ANTIALIAS)
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
        if self.timer:
            self.root.after_cancel(self.timer)
        self.bt_stop['state'] = 'disabled'
        self.bt_start['state'] = 'normal'
        self.bt_submit['state'] = 'normal'
        self.status_lbl['text'] = "Stopped"
        self.audio_data = self.recorder.stop()
        if self.audio_data is None:
            messagebox.showwarning("Warning", "No audio data recorded.")

    def submit(self):
        items = [i.strip() for i in self.ti.get("1.0", "end").splitlines() if i.strip()]
        costs = [c.strip().replace(",", ".") for c in self.tc.get("1.0", "end").splitlines() if c.strip()]
        if len(items) != len(costs):
            return messagebox.showwarning("Error", "Mismatch in items and costs")
        try:
            costs = [float(c) for c in costs]
        except:
            return messagebox.showwarning("Error", "Invalid cost format")
        if self.audio_data is None:
            return messagebox.showwarning("Error", "No audio")
        wav = encode_wav(self.audio_data)
        files = {"audio": ("r.wav", wav, "audio/wav")}
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
                    self.status_lbl['text'] = "Uploaded!"
                else:
                    raise Exception(r.text)
            except Exception as e:
                messagebox.showerror("Upload error", str(e))

        threading.Thread(target=upload).start()

    def on_frame_configure(self, event):
        # Update scrollregion after container changes size
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        # Set the inner frame's width to canvas's width to center content
        canvas_width = event.width
        self.canvas.itemconfig(self.window, width=canvas_width)

    def _on_mousewheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
