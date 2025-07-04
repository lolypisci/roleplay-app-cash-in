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
import time
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
        # Try loading fonts for PIL drawing (used in PDF/recibo generation)
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
                logo_lbl = tk.Label(header, text="ROLEFY", font=("Arial", 24, "bold"), bg=COLOR_BG)
                logo_lbl.pack(side="left")
        else:
            logo_lbl = tk.Label(header, text="ROLEFY", font=("Arial", 24, "bold"), bg=COLOR_BG)
            logo_lbl.pack(side="left")

        text_frame = Frame(header, bg=COLOR_BG)
        text_frame.pack(side="left", padx=5)

        tk.Label(text_frame, text="ROLEFY", font=("Jost-Bold", 24), bg=COLOR_BG, fg=COLOR_PRIMARY).pack(anchor="w")
        tk.Label(text_frame, text="Teacher: María Dolores Rivas Sánchez", font=("Lexend", 10), bg=COLOR_BG,
                 fg=COLOR_MUTED).pack(anchor="w")

        # Buyer entry
        self.ebuyer = self._add_entry("Buyer:")

        # Seller entry
        self.eseller = self._add_entry("Seller:")

        # Items and costs text boxes
        self.titems = self._add_text("Items (1 per line):")
        self.tcosts = self._add_text("Costs (1 per line):")

        # Handout preview image with proportional resize
        self.handout_label = None
        self.load_handout_preview()

        # Button Open Handout
        self.bt_open_handout = tk.Button(self.container, text="Open Handout", command=self.open_handout,
                                         bg=COLOR_ACCENT, fg="white", relief="flat")
        self.bt_open_handout.pack(pady=10)

        # Buttons frame
        btn_frame = Frame(self.container, bg=COLOR_BG)
        btn_frame.pack(pady=15)

        self.bt_start = self._styled_button("Start Recording", COLOR_PRIMARY, self.start_recording, btn_frame)
        self.bt_stop = self._styled_button("Stop Recording", "#FF6666", self.stop_recording, btn_frame)
        self.bt_submit = self._styled_button("Submit", COLOR_SECONDARY, self.submit, btn_frame)
        self.bt_download = self._styled_button("Download Receipt", COLOR_ACCENT, self.download_receipt, btn_frame)

        self.bt_stop["state"] = "disabled"
        self.bt_submit["state"] = "disabled"
        self.bt_download["state"] = "disabled"

        # Status and timer labels
        self.status_lbl = tk.Label(self.container, text="Ready", bg=COLOR_BG, fg=COLOR_TEXT)
        self.status_lbl.pack()
        self.timer_lbl = tk.Label(self.container, text="00:00", bg=COLOR_BG, fg="green")
        self.timer_lbl.pack()

        # Footer copyright with two lines centered
        footer = Frame(self.container, bg=COLOR_BG)
        footer.pack(side="bottom", pady=10)
        tk.Label(footer, text="Rolefy - Roleplay Evaluation App", font=("Lexend", 9), fg=COLOR_MUTED,
                 bg=COLOR_BG).pack()
        tk.Label(footer, text="© 2025 María Dolores Rivas Sánchez", font=("Lexend", 9), fg=COLOR_MUTED, bg=COLOR_BG).pack()

    def _add_entry(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5, fill="x", padx=20)
        lbl = tk.Label(frame, text=label_text, bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        lbl.pack(side="left")
        entry = tk.Entry(frame, font=("Lexend", 12))
        entry.pack(side="left", fill="x", expand=True, padx=10)
        return entry

    def _add_text(self, label_text):
        frame = Frame(self.container, bg=COLOR_BG)
        frame.pack(pady=5, fill="both", padx=20, expand=True)
        lbl = tk.Label(frame, text=label_text, bg=COLOR_BG, fg=COLOR_TEXT, font=("Lexend", 12))
        lbl.pack(anchor="w")
        txt = tk.Text(frame, height=5, font=("Lexend", 12))
        txt.pack(fill="both", expand=True)
        return txt

    def _styled_button(self, text, bg_color, cmd, parent):
        btn = tk.Button(parent, text=text, bg=bg_color, fg="white", relief="flat", font=("Lexend", 12), command=cmd)
        btn.pack(side="left", padx=10, ipadx=10, ipady=5)
        return btn

    def load_handout_preview(self):
        if not os.path.isfile(HANDOUT_PATH):
            if self.handout_label:
                self.handout_label.destroy()
            return

        try:
            img = Image.open(HANDOUT_PATH)
            max_w, max_h = 600, 400
            img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            self.handout_img_tk = ImageTk.PhotoImage(img)

            if self.handout_label:
                self.handout_label.configure(image=self.handout_img_tk)
            else:
                self.handout_label = tk.Label(self.container, image=self.handout_img_tk, bg=COLOR_BG)
                self.handout_label.pack(pady=10)

        except Exception as e:
            print("Error loading handout preview:", e)
            if self.handout_label:
                self.handout_label.destroy()
            self.handout_label = None

    def open_handout(self):
        # Abrir handout.png en el visualizador de imágenes predeterminado
        if os.path.isfile(HANDOUT_PATH):
            try:
                if os.name == 'nt':
                    os.startfile(HANDOUT_PATH)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.call(('open', HANDOUT_PATH))
                else:
                    import subprocess
                    subprocess.call(('xdg-open', HANDOUT_PATH))
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir el handout:\n{e}")
        else:
            messagebox.showinfo("Info", "No se encontró el handout.png")

    def start_recording(self):
        if self.recorder.recording:
            return
        self.status_lbl.config(text="Recording...")
        self.bt_start["state"] = "disabled"
        self.bt_stop["state"] = "normal"
        self.bt_submit["state"] = "disabled"
        self.bt_download["state"] = "disabled"

        self.seconds = 0
        self.update_timer()  # <-- esto hace que el temporizador avance cada segundo

        threading.Thread(target=self._record_thread, daemon=True).start()

    def _record_thread(self):
        self.recorder.start()
        while self.recorder.recording:
            time.sleep(0.1)
        self.audio_data = self.recorder.stop()

    def stop_recording(self):
        if not self.recorder.recording:
            return
        self.recorder.recording = False
        self.status_lbl.config(text="Recording stopped")
        self.bt_start["state"] = "normal"
        self.bt_stop["state"] = "disabled"
        self.bt_submit["state"] = "normal"

    def update_timer(self):
        mins = self.seconds // 60
        secs = self.seconds % 60
        self.timer_lbl.config(text=f"{mins:02d}:{secs:02d}")
        if self.recorder.recording:
            self.seconds += 1
            self.root.after(1000, self.update_timer)

    def submit(self):
        buyer = self.ebuyer.get().strip()
        seller = self.eseller.get().strip()
        items = self.titems.get("1.0", "end").strip()
        costs = self.tcosts.get("1.0", "end").strip()

        if not buyer or not seller:
            messagebox.showwarning("Warning", "Buyer and Seller names are required.")
            return
        if not items:
            messagebox.showwarning("Warning", "Please enter at least one item.")
            return
        if not costs:
            messagebox.showwarning("Warning", "Please enter costs.")
            return
        if self.audio_data is None or self.audio_data.size == 0:
            messagebox.showwarning("Warning", "Please record audio before submitting.")
            return

        # Prepare audio data in wav format bytes
        wav_bytes = encode_wav(self.audio_data)

        # Prepare multipart form data
        files = {'audio': ('recording.wav', wav_bytes, 'audio/wav')}
        data = {
            'comprador': buyer,
            'vendedor': seller,
            'productos': json.dumps(items.splitlines()),
            'costes': json.dumps(costs.splitlines())
        }

        try:
            resp = requests.post(f"{BACKEND}/upload", files=files, data=data)
            resp.raise_for_status()
            messagebox.showinfo("Success", "Roleplay uploaded successfully!")
            self.bt_submit["state"] = "disabled"
            self.bt_download["state"] = "normal"
            self._save_draft_clear()
        except Exception as e:
            messagebox.showerror("Failed to upload roleplay", str(e))

    def download_receipt(self):
        buyer = self.ebuyer.get().strip()
        seller = self.eseller.get().strip()
        items = self.titems.get("1.0", "end").strip().splitlines()
        costs = self.tcosts.get("1.0", "end").strip().splitlines()

        if not buyer or not seller or not items or not costs:
            messagebox.showwarning("Warning", "Complete buyer, seller, items, and costs before downloading receipt.")
            return

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, "ROLEFY Receipt", ln=True, align="C")
        pdf.set_font("Arial", "", 12)
        pdf.cell(0, 10, f"Buyer: {buyer}", ln=True)
        pdf.cell(0, 10, f"Seller: {seller}", ln=True)
        pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        pdf.ln(10)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Items and Costs:", ln=True)

        total = 0.0
        for item, cost in zip(items, costs):
            try:
                cost_float = float(cost.strip())
            except:
                cost_float = 0.0
            total += cost_float
            pdf.cell(0, 10, f"{item.strip()}: ${cost_float:.2f}", ln=True)

        pdf.ln(5)
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, f"Total: ${total:.2f}", ln=True)

        filename = f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        try:
            pdf.output(filename)
            messagebox.showinfo("Download", f"Receipt saved as {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save receipt:\n{e}")

    def _save_draft(self):
        draft = {
            "buyer": self.ebuyer.get(),
            "seller": self.eseller.get(),
            "items": self.titems.get("1.0", "end"),
            "costs": self.tcosts.get("1.0", "end")
        }
        try:
            with open("draft.json", "w", encoding="utf-8") as f:
                json.dump(draft, f)
        except Exception as e:
            print("Error saving draft:", e)

    def _load_draft(self):
        if os.path.isfile("draft.json"):
            try:
                with open("draft.json", "r", encoding="utf-8") as f:
                    draft = json.load(f)
                    self.ebuyer.insert(0, draft.get("buyer", ""))
                    self.eseller.insert(0, draft.get("seller", ""))
                    self.titems.insert("1.0", draft.get("items", ""))
                    self.tcosts.insert("1.0", draft.get("costs", ""))
            except Exception as e:
                print("Error loading draft:", e)

    def _save_draft_clear(self):
        try:
            if os.path.isfile("draft.json"):
                os.remove("draft.json")
        except Exception as e:
            print("Error clearing draft:", e)

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfig(self.window, width=canvas_width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")


def main():
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
