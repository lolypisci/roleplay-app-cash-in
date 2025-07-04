# --- student_app.py ---

import sounddevice as sd
import numpy as np
import wave
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog, Canvas, Frame, Scrollbar
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
import json
import requests
import os
from datetime import datetime
from fpdf import FPDF

CONFIG_URL = "https://raw.githubusercontent.com/lolypisci/roleplay-app-cash-in/main/config.json"
DEFAULT_BACKEND = "http://localhost:8000"
ASSETS_DIR = "assets"
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
HANDOUT_PATH = os.path.join("handouts", "handout.png")
LOGO_PATH = os.path.join(ASSETS_DIR, "logo.png")
BACKUP_DIR = "backups"

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
        url = simpledialog.askstring("Backend URL", "Enter backend URL:", initialvalue=DEFAULT_BACKEND)
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
            messagebox.showerror("Error", f"Could not start recording:\n{e}")

    def stop(self):
        try:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            return np.concatenate(self.frames, axis=0) if self.frames else None
        except Exception as e:
            messagebox.showerror("Error", f"Could not stop recording:\n{e}")
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
        root.minsize(700, 600)

        # Scrollable canvas setup
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

        self.recorder = Recorder()
        self.audio_data = None
        self.seconds = 0
        self.timer = None

        # Load fonts (Lexend, Jost, Nunito)
        self.fonts = {
            "Lexend": os.path.join(FONTS_DIR, "Lexend-Regular.ttf"),
            "Lexend-Bold": os.path.join(FONTS_DIR, "Lexend-SemiBold.ttf"),
            "Jost-Bold": os.path.join(FONTS_DIR, "Jost-Bold.ttf"),
            "Nunito-Bold": os.path.join(FONTS_DIR, "Nunito-Bold.ttf"),
        }

        self.load_fonts_for_pil()

        self._build_ui()
        self._load_draft()

    def load_fonts_for_pil(self):
        self.pil_fonts = {}
        for name, path in self.fonts.items():
            try:
                self.pil_fonts[name] = ImageFont.truetype(path, 18)
                self.pil_fonts[name + "_small"] = ImageFont.truetype(path, 12)
                self.pil_fonts[name + "_big"] = ImageFont.truetype(path, 24)
            except Exception:
                self.pil_fonts[name] = ImageFont.load_default()

    def _build_ui(self):
        header = Frame(self.container, bg=COLOR_BG)
        header.pack(pady=10)

        if os.path.exists(LOGO_PATH):
            try:
                logo_img = Image.open(LOGO_PATH)
                logo_img = logo_img.resize((50, 50), Image.Resampling.LANCZOS)
                self.logo_tk = ImageTk.PhotoImage(logo_img)
                logo_lbl = tk.Label(header, image=self.logo_tk, bg=COLOR_BG)
                logo_lbl.pack(side="left", padx=5)
            except Exception:
                pass

        title_lbl = tk.Label(header, text="ROLEFY", font=("Lexend-Bold", 36, "bold"), fg=COLOR_ACCENT, bg=COLOR_BG)
        title_lbl.pack(side="left", padx=10)

        subtitle_lbl = tk.Label(header, text="Student Roleplay Recorder", font=("Lexend", 14), fg=COLOR_MUTED, bg=COLOR_BG)
        subtitle_lbl.pack(side="left")

        # Form entries for comprador, vendedor, productos, costes
        form_frame = Frame(self.container, bg=COLOR_BG)
        form_frame.pack(pady=10, fill="x", padx=20)

        tk.Label(form_frame, text="Buyer Name:", font=("Lexend", 12), bg=COLOR_BG).grid(row=0, column=0, sticky="w")
        self.entry_comprador = tk.Entry(form_frame, font=("Lexend", 12))
        self.entry_comprador.grid(row=0, column=1, sticky="ew")

        tk.Label(form_frame, text="Seller Name:", font=("Lexend", 12), bg=COLOR_BG).grid(row=1, column=0, sticky="w")
        self.entry_vendedor = tk.Entry(form_frame, font=("Lexend", 12))
        self.entry_vendedor.grid(row=1, column=1, sticky="ew")

        tk.Label(form_frame, text="Items (one per line):", font=("Lexend", 12), bg=COLOR_BG).grid(row=2, column=0, sticky="nw")
        self.text_items = tk.Text(form_frame, height=5, font=("Lexend", 12))
        self.text_items.grid(row=2, column=1, sticky="ew")

        tk.Label(form_frame, text="Costs (one per line):", font=("Lexend", 12), bg=COLOR_BG).grid(row=3, column=0, sticky="nw")
        self.text_costs = tk.Text(form_frame, height=5, font=("Lexend", 12))
        self.text_costs.grid(row=3, column=1, sticky="ew")

        form_frame.columnconfigure(1, weight=1)

        # Record button and timer label
        self.btn_record = tk.Button(self.container, text="Start Recording", font=("Lexend-Bold", 14, "bold"), bg=COLOR_PRIMARY, command=self.toggle_recording)
        self.btn_record.pack(pady=10)

        self.lbl_timer = tk.Label(self.container, text="00:00", font=("Lexend-Bold", 14), fg=COLOR_ACCENT, bg=COLOR_BG)
        self.lbl_timer.pack()

        # Upload button
        self.btn_upload = tk.Button(self.container, text="Upload Roleplay", font=("Lexend-Bold", 14, "bold"), bg=COLOR_SECONDARY, command=self.upload_roleplay)
        self.btn_upload.pack(pady=10)

        # Status label
        self.lbl_status = tk.Label(self.container, text="", font=("Lexend", 12), fg=COLOR_MUTED, bg=COLOR_BG)
        self.lbl_status.pack()

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def toggle_recording(self):
        if self.recorder.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recorder.start()
        self.seconds = 0
        self.update_timer()
        self.btn_record.config(text="Stop Recording", bg="#FF6666")

    def stop_recording(self):
        data = self.recorder.stop()
        if data is not None:
            self.audio_data = data
            self.lbl_status.config(text="Recording stopped, ready to upload.")
        else:
            self.lbl_status.config(text="Recording failed.")
        self.btn_record.config(text="Start Recording", bg=COLOR_PRIMARY)
        self.stop_timer()

    def update_timer(self):
        self.lbl_timer.config(text=f"{self.seconds//60:02d}:{self.seconds%60:02d}")
        if self.recorder.recording:
            self.seconds += 1
            self.timer = self.root.after(1000, self.update_timer)

    def stop_timer(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None

    def upload_roleplay(self):
        comprador = self.entry_comprador.get().strip()
        vendedor = self.entry_vendedor.get().strip()
        productos_text = self.text_items.get("1.0", "end").strip()
        costes_text = self.text_costs.get("1.0", "end").strip()

        if not comprador or not vendedor:
            messagebox.showerror("Error", "Buyer and Seller names are required.")
            return
        if not productos_text:
            messagebox.showerror("Error", "Please enter at least one item.")
            return
        if not costes_text:
            messagebox.showerror("Error", "Please enter costs for items.")
            return
        if self.audio_data is None:
            messagebox.showerror("Error", "No audio recorded.")
            return

        productos = [line.strip() for line in productos_text.splitlines() if line.strip()]
        costes = [line.strip() for line in costes_text.splitlines() if line.strip()]

        if len(productos) != len(costes):
            messagebox.showerror("Error", "Number of items and costs must match.")
            return

        productos_json = json.dumps(productos)
        costes_json = json.dumps(costes)

        wav_bytes = encode_wav(self.audio_data)
        files = {
            "audio": ("roleplay.wav", wav_bytes, "audio/wav")
        }
        data = {
            "comprador": comprador,
            "vendedor": vendedor,
            "productos": productos_json,
            "costes": costes_json
        }

        try:
            self.lbl_status.config(text="Uploading...")
            response = requests.post(f"{BACKEND}/upload", data=data, files=files)
            if response.status_code == 200:
                self.lbl_status.config(text="Upload successful.")
                messagebox.showinfo("Success", "Roleplay uploaded successfully!")
                self._reset_form()
            else:
                self.lbl_status.config(text=f"Upload failed: {response.status_code} {response.text}")
                messagebox.showerror("Upload Failed", f"Server error: {response.status_code}")
        except Exception as e:
            self.lbl_status.config(text=f"Upload failed: {e}")
            messagebox.showerror("Upload Failed", f"Error: {e}")

    def _reset_form(self):
        self.entry_comprador.delete(0, "end")
        self.entry_vendedor.delete(0, "end")
        self.text_items.delete("1.0", "end")
        self.text_costs.delete("1.0", "end")
        self.audio_data = None
        self.lbl_timer.config(text="00:00")
        self.lbl_status.config(text="")

    def _load_draft(self):
        pass  # Placeholder to implement draft loading if needed

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
