import os
import subprocess
import threading
import zipfile
import shutil
import requests
from tkinter import *
from tkinter import messagebox, simpledialog, scrolledtext
from tkinter.ttk import Progressbar
from dotenv import load_dotenv
import webbrowser
import time

# Cargar variables .env
load_dotenv()
RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
PROJECT_ID = os.getenv("PROJECT_ID")

# Configuración URL app
TEACHER_VIEW_URL = "https://roleplay-app-cash-in-production.up.railway.app"
STUDENT_APP_PATH = "student_app.py"
REPO_PATH = os.getcwd()

# Colores elegantes y profesionales
BG_COLOR = "#f0f4f8"
BTN_COLOR = "#4a90e2"
BTN_HOVER = "#357ABD"
TXT_COLOR = "#333333"
FONT = ("Segoe UI", 11)

class LauncherApp:
    def __init__(self, root):
        self.root = root
        root.title("Roleplay App Launcher")
        root.geometry("500x480")
        root.config(bg=BG_COLOR)
        root.resizable(False, False)

        # Título
        Label(root, text="Roleplay App Control Panel", font=("Segoe UI", 16, "bold"),
              bg=BG_COLOR, fg=BTN_COLOR).pack(pady=15)

        # Estado conexión
        self.status_var = StringVar(value="Checking server status...")
        self.status_label = Label(root, textvariable=self.status_var, font=FONT,
                                  bg=BG_COLOR, fg=TXT_COLOR)
        self.status_label.pack(pady=5)

        # Botones
        self.create_button("Open Teacher View", self.open_teacher_view)
        self.create_button("Open Student App", self.open_student_app)
        self.create_button("Update Code (Git)", self.update_code)
        self.create_button("Restart Railway Project", self.restart_railway)
        self.create_button("Backup DB and Audios", self.backup_files)
        self.create_button("Show Uploads History", self.show_history)

        # Barra progreso (para actualizaciones y reinicios)
        self.progress = Progressbar(root, orient=HORIZONTAL, length=380, mode='indeterminate')
        self.progress.pack(pady=20)

        # Verificar conexión al arrancar
        threading.Thread(target=self.check_server_online, daemon=True).start()

    def create_button(self, text, command):
        btn = Button(self.root, text=text, font=FONT, bg=BTN_COLOR, fg="white",
                     activebackground=BTN_HOVER, activeforeground="white",
                     relief="flat", cursor="hand2", command=command)
        btn.pack(fill='x', padx=50, pady=8)
        # Añadir efecto hover
        btn.bind("<Enter>", lambda e: btn.config(bg=BTN_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=BTN_COLOR))

    def open_teacher_view(self):
        webbrowser.open_new_tab(TEACHER_VIEW_URL)

    def open_student_app(self):
        # Ejecutar student_app.py en nueva consola independiente
        if not os.path.isfile(STUDENT_APP_PATH):
            messagebox.showerror("Error", f"{STUDENT_APP_PATH} not found!")
            return
        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(["start", "cmd", "/k", f"python {STUDENT_APP_PATH}"], shell=True)
            else:
                subprocess.Popen(["x-terminal-emulator", "-e", f"python3 {STUDENT_APP_PATH}"])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open student app:\n{e}")

    def update_code(self):
        msg = simpledialog.askstring("Commit message", "Enter commit message:")
        if not msg:
            return
        self.progress.start()
        threading.Thread(target=self._git_update_thread, args=(msg,), daemon=True).start()

    def _git_update_thread(self, msg):
        try:
            cmds = [
                ["git", "pull"],
                ["git", "add", "."],
                ["git", "commit", "-m", msg],
                ["git", "push"]
            ]
            for c in cmds:
                result = subprocess.run(c, cwd=REPO_PATH, capture_output=True, text=True)
                if result.returncode != 0 and "nothing to commit" not in result.stderr.lower():
                    self.progress.stop()
                    messagebox.showerror("Git Error", f"Command {' '.join(c)} failed:\n{result.stderr}")
                    return
            self.progress.stop()
            messagebox.showinfo("Success", "Code updated successfully!")
        except Exception as e:
            self.progress.stop()
            messagebox.showerror("Error", f"Git update failed:\n{e}")

    def restart_railway(self):
        if not RAILWAY_TOKEN or not PROJECT_ID:
            messagebox.showerror("Config error", "RAILWAY_TOKEN or PROJECT_ID missing in .env")
            return
        if not messagebox.askyesno("Confirm", "Are you sure to restart Railway project?"):
            return
        self.progress.start()
        threading.Thread(target=self._railway_restart_thread, daemon=True).start()

    def _railway_restart_thread(self):
        try:
            url = f"https://backboard.railway.app/api/v1/projects/{PROJECT_ID}/deploys"
            headers = {"Authorization": f"Bearer {RAILWAY_TOKEN}"}
            response = requests.post(url, headers=headers)
            if response.status_code == 201:
                self.progress.stop()
                messagebox.showinfo("Success", "Railway project restart triggered!")
            else:
                self.progress.stop()
                messagebox.showerror("Error", f"Railway API error: {response.status_code}\n{response.text}")
        except Exception as e:
            self.progress.stop()
            messagebox.showerror("Error", f"Railway restart failed:\n{e}")

    def backup_files(self):
        backup_name = f"backup_roleplay_{time.strftime('%Y%m%d_%H%M%S')}.zip"
        try:
            with zipfile.ZipFile(backup_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Añadir base de datos
                if os.path.isfile("roleplay.db"):
                    zipf.write("roleplay.db")
                # Añadir audios
                audios_dir = "uploads"
                if os.path.isdir(audios_dir):
                    for rootdir, _, files in os.walk(audios_dir):
                        for file in files:
                            zipf.write(os.path.join(rootdir, file))
            messagebox.showinfo("Backup created", f"Backup saved as {backup_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup failed:\n{e}")

    def show_history(self):
        try:
            # Traer últimos 10 roleplays desde backend
            url = f"{TEACHER_VIEW_URL}/roleplays"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                raise Exception(f"Status code {resp.status_code}")
            data = resp.json()
            # Solo últimos 10 ordenados por timestamp descendente
            last_10 = sorted(data, key=lambda x: x["timestamp"], reverse=True)[:10]

            win = Toplevel(self.root)
            win.title("Last 10 Uploads")
            win.geometry("520x400")
            win.config(bg=BG_COLOR)
            txt = scrolledtext.ScrolledText(win, font=("Segoe UI", 10))
            txt.pack(fill=BOTH, expand=True, padx=10, pady=10)

            for i, r in enumerate(last_10, 1):
                products = ", ".join(r.get("productos", []))
                costs = ", ".join(str(c) for c in r.get("costes", []))
                txt.insert(END, f"{i}. Buyer: {r['comprador']}\n   Seller: {r['vendedor']}\n"
                               f"   Products: {products}\n   Costs: {costs}\n"
                               f"   Timestamp: {r['timestamp']}\n\n")
            txt.config(state=DISABLED)
        except Exception as e:
            messagebox.showerror("Error", f"Could not fetch uploads:\n{e}")

    def check_server_online(self):
        try:
            resp = requests.get(TEACHER_VIEW_URL, timeout=6)
            if resp.status_code == 200:
                self.status_var.set("Server status: ONLINE")
                self.status_label.config(fg="green")
            else:
                self.status_var.set("Server status: OFFLINE or unreachable")
                self.status_label.config(fg="red")
        except Exception:
            self.status_var.set("Server status: OFFLINE or unreachable")
            self.status_label.config(fg="red")


if __name__ == "__main__":
    root = Tk()
    app = LauncherApp(root)
    root.mainloop()
