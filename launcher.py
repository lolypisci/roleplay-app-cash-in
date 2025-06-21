import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import os
import datetime

# CONFIGURACIÓN: Cambia estas rutas y URLs según tu proyecto
GIT_BAT_PATH = "git_push.bat"  # ruta al .bat que haces git add/commit/push
STUDENT_APP_SCRIPT = "student_app.py"  # ruta al script de la app estudiante
TEACHER_URL = "https://roleplay-app-cash-in-production.up.railway.app/"
STUDENT_URL = "https://roleplay-app-cash-in-production.up.railway.app/student"

LOG_FILE = "update_log.txt"

def log_to_file(text):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(text + "\n")

def run_update():
    def task():
        output_text.config(state=tk.NORMAL)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, f"Starting update at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_to_file(f"--- Update started at {datetime.datetime.now()} ---")
        try:
            # Ejecutar el batch file
            process = subprocess.Popen(GIT_BAT_PATH, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True)
            for line in process.stdout:
                output_text.insert(tk.END, line)
                output_text.see(tk.END)
                log_to_file(line.strip())
            process.wait()
            if process.returncode == 0:
                output_text.insert(tk.END, "\nUpdate completed successfully.\n")
                log_to_file("Update completed successfully.\n")
            else:
                output_text.insert(tk.END, f"\nUpdate failed with code {process.returncode}\n")
                log_to_file(f"Update failed with code {process.returncode}\n")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run update: {e}")
            log_to_file(f"Exception: {e}")
        output_text.config(state=tk.DISABLED)

    threading.Thread(target=task, daemon=True).start()

def open_teacher_view():
    webbrowser.open(TEACHER_URL)

def open_student_app():
    webbrowser.open(STUDENT_URL)

def run_student_script():
    def task():
        try:
            # Abrir nuevo terminal con la app del estudiante (solo Windows)
            # Esto abre una consola y ejecuta python student_app.py y mantiene ventana abierta
            cmd = f'start cmd /k python "{STUDENT_APP_SCRIPT}"'
            subprocess.Popen(cmd, shell=True)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch student app: {e}")
    threading.Thread(target=task, daemon=True).start()

app = tk.Tk()
app.title("Roleplay App Launcher")
app.geometry("700x450")

frame = tk.Frame(app)
frame.pack(pady=10)

btn_update = tk.Button(frame, text="Update Code (Git)", command=run_update, width=20)
btn_update.grid(row=0, column=0, padx=5)

btn_teacher = tk.Button(frame, text="Open Teacher View", command=open_teacher_view, width=20)
btn_teacher.grid(row=0, column=1, padx=5)

btn_student_web = tk.Button(frame, text="Open Student App (Web)", command=open_student_app, width=20)
btn_student_web.grid(row=0, column=2, padx=5)

btn_student_script = tk.Button(frame, text="Run Student App (Python)", command=run_student_script, width=25)
btn_student_script.grid(row=1, column=0, columnspan=3, pady=10)

output_text = scrolledtext.ScrolledText(app, wrap=tk.WORD, height=18, state=tk.DISABLED)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

app.mainloop()
