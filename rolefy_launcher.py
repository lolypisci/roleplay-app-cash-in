# --- rolefy_launcher.py ---

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, Canvas, Frame, Scrollbar, Text
import requests
import json
import threading
import io
import wave
import sounddevice as sd
import numpy as np
import os

BACKEND = "http://localhost:8000"  # Cambiar por la URL en producción, o configurar

# --- Grabadora para rolefy_launcher.py (para hacer grabación y subir audio) ---
SAMPLE_RATE = 44100
CHANNELS = 1

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
            messagebox.showerror("Error", f"Could not start recording:\n{e}")

    def stop(self):
        try:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            if self.frames:
                return np.concatenate(self.frames, axis=0)
            return None
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

class RolefyLauncherApp:
    def __init__(self, root):
        self.root = root
        root.title("ROLEFY – Teacher View")
        root.geometry("1000x700")

        # Variables de grabación
        self.recorder = Recorder()
        self.audio_data = None
        self.recording = False
        self.seconds = 0
        self.timer = None

        self._build_ui()
        self.fetch_roleplays()

    def _build_ui(self):
        # Header con nombre ROLEFY destacado
        header = tk.Frame(self.root)
        header.pack(pady=10)
        title_lbl = tk.Label(header, text="ROLEFY", font=("Lexend", 40, "bold"), fg="#1E90FF")
        title_lbl.pack()

        # Formulario para grabar y subir nuevo roleplay
        form_frame = tk.Frame(self.root)
        form_frame.pack(pady=10, fill="x", padx=20)

        tk.Label(form_frame, text="Buyer Name:", font=("Lexend", 12)).grid(row=0, column=0, sticky="w")
        self.entry_comprador = tk.Entry(form_frame, font=("Lexend", 12))
        self.entry_comprador.grid(row=0, column=1, sticky="ew")

        tk.Label(form_frame, text="Seller Name:", font=("Lexend", 12)).grid(row=1, column=0, sticky="w")
        self.entry_vendedor = tk.Entry(form_frame, font=("Lexend", 12))
        self.entry_vendedor.grid(row=1, column=1, sticky="ew")

        tk.Label(form_frame, text="Items (one per line):", font=("Lexend", 12)).grid(row=2, column=0, sticky="nw")
        self.text_items = tk.Text(form_frame, height=5, font=("Lexend", 12))
        self.text_items.grid(row=2, column=1, sticky="ew")

        tk.Label(form_frame, text="Costs (one per line):", font=("Lexend", 12)).grid(row=3, column=0, sticky="nw")
        self.text_costs = tk.Text(form_frame, height=5, font=("Lexend", 12))
        self.text_costs.grid(row=3, column=1, sticky="ew")

        form_frame.columnconfigure(1, weight=1)

        # Botones grabar/parar y subir
        self.btn_record = tk.Button(form_frame, text="Start Recording", font=("Lexend", 12, "bold"), bg="#A9E5BB", command=self.toggle_recording)
        self.btn_record.grid(row=4, column=0, pady=10)

        self.btn_upload = tk.Button(form_frame, text="Upload Roleplay", font=("Lexend", 12, "bold"), bg="#89DCEB", command=self.upload_roleplay)
        self.btn_upload.grid(row=4, column=1, pady=10, sticky="ew")

        self.lbl_timer = tk.Label(form_frame, text="00:00", font=("Lexend", 12), fg="#1E90FF")
        self.lbl_timer.grid(row=5, column=0, columnspan=2)

        # Status
        self.lbl_status = tk.Label(self.root, text="", fg="#333")
        self.lbl_status.pack()

        # Tabla con roleplays
        self.tree = ttk.Treeview(self.root, columns=("ID", "Buyer", "Seller", "Timestamp", "Feedback", "Nota"), show="headings")
        for col in ("ID", "Buyer", "Seller", "Timestamp", "Feedback", "Nota"):
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center")
        self.tree.pack(expand=True, fill="both", padx=20, pady=10)

        self.tree.bind("<Double-1>", self.on_row_double_click)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # Botón refresh
        btn_refresh = tk.Button(self.root, text="Refresh Roleplays", command=self.fetch_roleplays)
        btn_refresh.pack(pady=5)

    def on_frame_configure(self, event=None):
        pass

    def toggle_recording(self):
        if self.recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        self.recorder.start()
        self.recording = True
        self.seconds = 0
        self.update_timer()
        self.btn_record.config(text="Stop Recording", bg="#FF6666")

    def stop_recording(self):
        data = self.recorder.stop()
        self.recording = False
        if data is not None:
            self.audio_data = data
            self.lbl_status.config(text="Recording stopped, ready to upload.")
        else:
            self.lbl_status.config(text="Recording failed.")
        self.btn_record.config(text="Start Recording", bg="#A9E5BB")
        self.stop_timer()

    def update_timer(self):
        self.lbl_timer.config(text=f"{self.seconds//60:02d}:{self.seconds%60:02d}")
        if self.recording:
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

        def do_upload():
            try:
                self.lbl_status.config(text="Uploading...")
                response = requests.post(f"{BACKEND}/upload", data=data, files=files)
                if response.status_code == 200:
                    self.lbl_status.config(text="Upload successful.")
                    messagebox.showinfo("Success", "Roleplay uploaded successfully!")
                    self._reset_form()
                    self.fetch_roleplays()
                else:
                    self.lbl_status.config(text=f"Upload failed: {response.status_code} {response.text}")
                    messagebox.showerror("Upload Failed", f"Server error: {response.status_code}")
            except Exception as e:
                self.lbl_status.config(text=f"Upload failed: {e}")
                messagebox.showerror("Upload Failed", f"Error: {e}")

        threading.Thread(target=do_upload).start()

    def _reset_form(self):
        self.entry_comprador.delete(0, "end")
        self.entry_vendedor.delete(0, "end")
        self.text_items.delete("1.0", "end")
        self.text_costs.delete("1.0", "end")
        self.audio_data = None
        self.lbl_timer.config(text="00:00")
        self.lbl_status.config("")

    def fetch_roleplays(self):
        def fetch():
            try:
                resp = requests.get(f"{BACKEND}/roleplays")
                if resp.status_code == 200:
                    data = resp.json()
                    self._populate_table(data)
                else:
                    self.lbl_status.config(text=f"Failed to fetch: {resp.status_code}")
            except Exception as e:
                self.lbl_status.config(text=f"Error fetching data: {e}")
        threading.Thread(target=fetch).start()

    def _populate_table(self, data):
        self.tree.delete(*self.tree.get_children())
        for item in data:
            self.tree.insert("", "end", values=(
                item["id"],
                item["comprador"],
                item["vendedor"],
                item["timestamp"].replace("T", " ").split(".")[0],
                item.get("feedback", ""),
                item.get("nota", "")
            ))

    def on_row_double_click(self, event):
        item_id = self.tree.focus()
        if not item_id:
            return
        values = self.tree.item(item_id)["values"]
        roleplay_id = values[0]

        # Abrir ventana para editar feedback y nota
        self.edit_feedback_window(roleplay_id, values)

    def edit_feedback_window(self, roleplay_id, values):
        win = tk.Toplevel(self.root)
        win.title(f"Edit Feedback - Roleplay {roleplay_id}")
        win.geometry("400x300")

        tk.Label(win, text="Feedback:").pack(pady=5)
        txt_feedback = tk.Text(win, height=5)
        txt_feedback.pack(fill="both", padx=10)
        txt_feedback.insert("1.0", values[4] if values[4] else "")

        tk.Label(win, text="Nota:").pack(pady=5)
        entry_nota = tk.Entry(win)
        entry_nota.pack(fill="x", padx=10)
        entry_nota.insert(0, values[5] if values[5] else "")

        def save():
            feedback = txt_feedback.get("1.0", "end").strip()
            nota = entry_nota.get().strip()
            try:
                resp = requests.post(f"{BACKEND}/update_feedback", json={
                    "id": roleplay_id,
                    "feedback": feedback,
                    "nota": nota
                })
                if resp.status_code == 200 and resp.json().get("status") == "ok":
                    messagebox.showinfo("Saved", "Feedback updated.")
                    self.fetch_roleplays()
                    win.destroy()
                else:
                    messagebox.showerror("Error", "Failed to update feedback.")
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}")

        btn_save = tk.Button(win, text="Save", command=save)
        btn_save.pack(pady=10)

def main():
    root = tk.Tk()
    app = RolefyLauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
