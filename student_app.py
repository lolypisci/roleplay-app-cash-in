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

# Configuración
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
        # Header with logo and text
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
        text_frame.pack(side="left", padx=5)

        tk.Label(text_frame, text="ROLEFY", font=("Jost-Bold", 20), bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="w")
        tk.Label(text_frame, text="Teacher: María Dolores Rivas Sánchez", font=("Lexend", 10), bg=COLOR_BG,
                 fg=COLOR_MUTED).pack(anchor="w")

        # Buyer entry
        self.ebuyer = self._add_entry("Buyer:")

        # Seller entry
        self.eseller = self._add_entry("Seller:")

        # Items and costs text boxes
        self.titems = self._add_text("Items (1 per line):")
        self.tcosts = self._add_text("Costs (same count):")

        # Handout preview image with proportional resize
        self.handout_label = None
        self.load_handout_preview()

        # Button Open Handout
        self.bt_open_handout = tk.Button(self.container, text="Open Handout", command=self.open_handout,
                                        bg=COLOR_SECONDARY, fg=COLOR_TEXT, font=("Lexend-Bold", 12), relief="raised",
                                        bd=2)
        self.bt_open_handout.pack(pady=5)

        # Timer label
        self.lbl_timer = tk.Label(self.container, text="00:00", font=("Lexend-Bold", 24), fg=COLOR_ACCENT, bg=COLOR_BG)
        self.lbl_timer.pack(pady=5)

        # Start / Stop recording button
        self.bt_record = tk.Button(self.container, text="Start Recording", command=self.toggle_recording,
                                   bg=COLOR_PRIMARY, fg=COLOR_TEXT, font=("Lexend-Bold", 14), relief="raised", bd=2)
        self.bt_record.pack(pady=10)

        # Upload button
        self.bt_upload = tk.Button(self.container, text="Upload Roleplay", command=self.upload_roleplay,
                                   bg=COLOR_SECONDARY, fg=COLOR_TEXT, font=("Lexend-Bold", 14), relief="raised", bd=2)
        self.bt_upload.pack(pady=10)

        # Feedback & note area (hidden until upload)
        self.feedback_label = tk.Label(self.container, text="Feedback:", bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        self.feedback_entry = tk.Text(self.container, height=4, width=40, font=("Lexend", 12))

        self.note_label = tk.Label(self.container, text="Grade:", bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        self.note_entry = tk.Text(self.container, height=1, width=10, font=("Lexend", 12))

        # Receipt preview button
        self.bt_receipt = tk.Button(self.container, text="Generate Receipt", command=self.generate_receipt,
                                    bg=COLOR_SECONDARY, fg=COLOR_TEXT, font=("Lexend-Bold", 14), relief="raised", bd=2)
        self.bt_receipt.pack(pady=10)
        self.bt_receipt.config(state="disabled")

    def _add_entry(self, label_text):
        frame = tk.Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5, fill="x", padx=10)
        label = tk.Label(frame, text=label_text, bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        label.pack(side="left", padx=(0, 5))
        entry = tk.Entry(frame, font=("Lexend", 12), width=40)
        entry.pack(side="left", fill="x", expand=True)
        return entry

    def _add_text(self, label_text):
        frame = tk.Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5, fill="both", expand=False, padx=10)
        label = tk.Label(frame, text=label_text, bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        label.pack(anchor="w")
        text = tk.Text(frame, height=5, font=("Lexend", 12))
        text.pack(fill="both", expand=True)
        return text

    def load_handout_preview(self):
        if os.path.exists(HANDOUT_PATH):
            try:
                hand_img = Image.open(HANDOUT_PATH)
                max_w, max_h = 600, 300
                w, h = hand_img.size
                ratio = min(max_w / w, max_h / h)
                hand_img = hand_img.resize((int(w * ratio), int(h * ratio)), Image.Resampling.LANCZOS)
                self.handout_imgtk = ImageTk.PhotoImage(hand_img)
                if self.handout_label:
                    self.handout_label.configure(image=self.handout_imgtk)
                else:
                    self.handout_label = tk.Label(self.container, image=self.handout_imgtk, bg=COLOR_BG)
                    self.handout_label.pack(pady=5)
            except Exception as e:
                print(f"Error loading handout image: {e}")

    def open_handout(self):
        if os.path.exists(HANDOUT_PATH):
            os.startfile(HANDOUT_PATH) if os.name == "nt" else os.system(f'xdg-open "{HANDOUT_PATH}"')
        else:
            messagebox.showwarning("Handout", "Handout image not found.")

    def toggle_recording(self):
        if not self.recorder.recording:
            # Start recording
            buyer = self.ebuyer.get().strip()
            seller = self.eseller.get().strip()
            if not buyer or not seller:
                messagebox.showerror("Missing Data", "Please enter Buyer and Seller names before recording.")
                return
            self.recorder.start()
            self.bt_record.config(text="Stop Recording", bg="#FF6B6B")
            self.seconds = 0
            self._update_timer()
        else:
            # Stop recording
            self.audio_data = self.recorder.stop()
            self.bt_record.config(text="Start Recording", bg=COLOR_PRIMARY)
            if self.timer:
                self.root.after_cancel(self.timer)
            self.lbl_timer.config(text="00:00")

    def _update_timer(self):
        mins = self.seconds // 60
        secs = self.seconds % 60
        self.lbl_timer.config(text=f"{mins:02d}:{secs:02d}")
        if self.recorder.recording:
            self.seconds += 1
            self.timer = self.root.after(1000, self._update_timer)

    def upload_roleplay(self):
        if self.recorder.recording:
            messagebox.showerror("Recording", "Please stop recording before uploading.")
            return
        if not self.audio_data.any():
            messagebox.showerror("No audio", "No audio recorded to upload.")
            return
        comprador = self.ebuyer.get().strip()
        vendedor = self.eseller.get().strip()
        productos = self.titems.get("1.0", "end").strip().splitlines()
        costes = self.tcosts.get("1.0", "end").strip().splitlines()

        if not comprador or not vendedor:
            messagebox.showerror("Missing Data", "Buyer and Seller names are required.")
            return
        if len(productos) != len(costes):
            messagebox.showerror("Data mismatch", "Number of items and costs must match.")
            return

        productos_json = json.dumps(productos)
        costes_json = json.dumps(costes)

        audio_bytes = encode_wav(self.audio_data)

        files = {
            "audio": ("roleplay.wav", audio_bytes, "audio/wav")
        }
        data = {
            "comprador": comprador,
            "vendedor": vendedor,
            "productos": productos_json,
            "costes": costes_json
        }

        try:
            resp = requests.post(f"{BACKEND}/upload", data=data, files=files)
            resp.raise_for_status()
            result = resp.json()
            if result.get("status") == "ok":
                messagebox.showinfo("Upload", "Roleplay uploaded successfully!")
                self._save_draft(clear=True)
                self.bt_receipt.config(state="normal")
            else:
                messagebox.showerror("Upload error", f"Server error: {result.get('message', 'Unknown error')}")
        except Exception as e:
            messagebox.showerror("Upload error", f"Failed to upload roleplay:\n{e}")

    def generate_receipt(self):
        comprador = self.ebuyer.get().strip()
        vendedor = self.eseller.get().strip()
        productos = self.titems.get("1.0", "end").strip().splitlines()
        costes = self.tcosts.get("1.0", "end").strip().splitlines()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Crear PDF recibo simple con FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ROLEFY - Recibo de compra", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Comprador: {comprador}", ln=True)
        pdf.cell(0, 10, f"Vendedor: {vendedor}", ln=True)
        pdf.cell(0, 10, f"Fecha: {now}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(100, 10, "Producto")
        pdf.cell(40, 10, "Precio", ln=True)
        pdf.set_font("Arial", "", 12)
        total = 0.0
        for prod, cost in zip(productos, costes):
            pdf.cell(100, 10, prod)
            pdf.cell(40, 10, cost, ln=True)
            try:
                total += float(cost.replace(",", "."))
            except:
                pass
        pdf.ln(10)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(100, 10, "Total")
        pdf.cell(40, 10, f"{total:.2f}", ln=True)

        # Guardar PDF
        save_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Save Receipt"
        )
        if save_path:
            pdf.output(save_path)
            messagebox.showinfo("Receipt", f"Receipt saved to:\n{save_path}")

    def _save_draft(self, clear=False):
        # Guardar datos en un archivo local para recuperación (por ejemplo draft.json)
        draft_path = "draft.json"
        if clear:
            if os.path.exists(draft_path):
                os.remove(draft_path)
            return
        data = {
            "comprador": self.ebuyer.get(),
            "vendedor": self.eseller.get(),
            "productos": self.titems.get("1.0", "end"),
            "costes": self.tcosts.get("1.0", "end"),
        }
        with open(draft_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    def _load_draft(self):
        draft_path = "draft.json"
        if os.path.exists(draft_path):
            try:
                with open(draft_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.ebuyer.insert(0, data.get("comprador", ""))
                self.eseller.insert(0, data.get("vendedor", ""))
                self.titems.insert("1.0", data.get("productos", ""))
                self.tcosts.insert("1.0", data.get("costes", ""))
            except Exception:
                pass

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
