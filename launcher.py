import os
import shutil
import subprocess
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import messagebox, ttk
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuración inicial
GIT_COMMAND = "git"
RAILWAY_API_TOKEN = os.getenv("RAILWAY_TOKEN")
RAILWAY_PROJECT_ID = os.getenv("PROJECT_ID")
BACKUP_FOLDER = "updates"
UPLOADS_FOLDER = "uploads"
DATABASE_FILE = "roleplay.db"

class LauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Roleplay App Launcher")
        self.root.geometry("450x420")
        self.root.configure(bg="#f0f4f8")

        # Estilo ttk
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 11), padding=6)
        style.configure('TLabel', background="#f0f4f8", font=('Segoe UI', 12))
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))

        ttk.Label(root, text="Roleplay App Launcher", style='Header.TLabel').pack(pady=15)

        self.status_text = tk.StringVar()
        self.status_text.set("Ready")
        ttk.Label(root, textvariable=self.status_text).pack(pady=(0,15))

        # Botones
        ttk.Button(root, text="Open Teacher View", command=self.open_teacher_view).pack(fill="x", padx=40, pady=5)
        ttk.Button(root, text="Open Student App", command=self.open_student_app).pack(fill="x", padx=40, pady=5)
        ttk.Button(root, text="Update Code (Git)", command=self.update_code).pack(fill="x", padx=40, pady=5)
        ttk.Button(root, text="Restart Railway Project", command=self.restart_railway).pack(fill="x", padx=40, pady=5)
        ttk.Button(root, text="Backup Data & Audios", command=self.backup_data).pack(fill="x", padx=40, pady=5)
        ttk.Button(root, text="Show Uploads History", command=self.show_uploads_history).pack(fill="x", padx=40, pady=5)

        # Text box para mostrar logs o historial
        self.log_text = tk.Text(root, height=7, width=50, state="disabled", bg="#eaeef3", font=("Consolas", 10))
        self.log_text.pack(padx=15, pady=15, fill="both", expand=True)

    def log(self, message):
        self.log_text.config(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def open_teacher_view(self):
        url = "http://localhost:8000/"  # Cambia si es otro puerto o url remota
        self.log(f"Opening Teacher View at {url}")
        webbrowser.open(url)

    def open_student_app(self):
        url = "http://localhost:8000/student"  # Cambia si es otro puerto o url remota
        self.log(f"Opening Student App at {url}")
        webbrowser.open(url)

    def check_internet(self):
        self.log("Checking internet connection...")
        try:
            requests.get("https://api.github.com", timeout=5)
            self.log("Internet connection OK")
            return True
        except requests.RequestException:
            self.log("No internet connection")
            messagebox.showerror("Error", "No internet connection detected. Please check your network.")
            return False

    def update_code(self):
        if not self.check_internet():
            return
        def run_update():
            self.log("Starting git update...")

            # git pull para actualizar repositorio
            pull_cmd = [GIT_COMMAND, "pull"]
            result_pull = subprocess.run(pull_cmd, capture_output=True, text=True)
            self.log(result_pull.stdout)
            if result_pull.returncode != 0:
                self.log(f"Error during git pull:\n{result_pull.stderr}")
                messagebox.showerror("Git Error", f"Git pull failed:\n{result_pull.stderr}")
                return

            # git add para añadir solo código fuente (ignorar dist, updates, etc)
            add_cmd = [GIT_COMMAND, "add", "*.py", "*.json", "*.md", "*.env", "*.bat", "*.txt", "static/", "templates/"]
            result_add = subprocess.run(add_cmd, capture_output=True, text=True)
            self.log(result_add.stdout)
            if result_add.returncode != 0:
                self.log(f"Error during git add:\n{result_add.stderr}")
                messagebox.showerror("Git Error", f"Git add failed:\n{result_add.stderr}")
                return

            # git commit -m "update via launcher"
            commit_msg = "Update via launcher"
            commit_cmd = [GIT_COMMAND, "commit", "-m", commit_msg]
            result_commit = subprocess.run(commit_cmd, capture_output=True, text=True)
            if result_commit.returncode != 0:
                if "nothing to commit" in result_commit.stderr.lower():
                    self.log("No changes to commit.")
                else:
                    self.log(f"Error during git commit:\n{result_commit.stderr}")
                    messagebox.showerror("Git Error", f"Git commit failed:\n{result_commit.stderr}")
                    return
            else:
                self.log(result_commit.stdout)

            # git push
            push_cmd = [GIT_COMMAND, "push"]
            result_push = subprocess.run(push_cmd, capture_output=True, text=True)
            self.log(result_push.stdout)
            if result_push.returncode != 0:
                self.log(f"Error during git push:\n{result_push.stderr}")
                messagebox.showerror("Git Error", f"Git push failed:\n{result_push.stderr}")
                return

            self.log("Git update completed successfully.")

        threading.Thread(target=run_update, daemon=True).start()

    def restart_railway(self):
        if not RAILWAY_API_TOKEN or not RAILWAY_PROJECT_ID:
            messagebox.showerror("Config Error", "Railway API token or Project ID not set in .env")
            self.log("Missing Railway API token or project ID.")
            return
        if not self.check_internet():
            return

        def run_restart():
            self.log("Restarting Railway project...")
            url = f"https://api.railway.app/v1/projects/{RAILWAY_PROJECT_ID}/deployments"
            headers = {
                "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
                "Content-Type": "application/json"
            }
            try:
                response = requests.post(url, headers=headers)
                if response.status_code == 201 or response.status_code == 200:
                    self.log("Railway project restarted successfully.")
                    messagebox.showinfo("Success", "Railway project restarted successfully.")
                else:
                    self.log(f"Railway API error: {response.status_code} {response.text}")
                    messagebox.showerror("Railway API Error", f"Error: {response.status_code}\n{response.text}")
            except requests.RequestException as e:
                self.log(f"Request error: {str(e)}")
                messagebox.showerror("Network Error", f"Request failed:\n{str(e)}")

        threading.Thread(target=run_restart, daemon=True).start()

    def backup_data(self):
        try:
            os.makedirs(BACKUP_FOLDER, exist_ok=True)

            # Backup DB
            if os.path.isfile(DATABASE_FILE):
                shutil.copy2(DATABASE_FILE, os.path.join(BACKUP_FOLDER, DATABASE_FILE))
                self.log(f"Database backed up to {BACKUP_FOLDER}/{DATABASE_FILE}")
            else:
                self.log("Database file not found, skipping DB backup.")

            # Backup audio files
            if os.path.isdir(UPLOADS_FOLDER):
                backup_audio_folder = os.path.join(BACKUP_FOLDER, "uploads_backup")
                if os.path.isdir(backup_audio_folder):
                    shutil.rmtree(backup_audio_folder)
                shutil.copytree(UPLOADS_FOLDER, backup_audio_folder)
                self.log(f"Audio files backed up to {backup_audio_folder}")
            else:
                self.log("Uploads folder not found, skipping audio backup.")

            messagebox.showinfo("Backup Complete", f"Backup completed successfully in folder: {BACKUP_FOLDER}")
        except Exception as e:
            self.log(f"Backup failed: {str(e)}")
            messagebox.showerror("Backup Error", f"Backup failed:\n{str(e)}")

    def show_uploads_history(self):
        if not os.path.isdir(UPLOADS_FOLDER):
            self.log("Uploads folder not found.")
            messagebox.showwarning("Warning", "Uploads folder not found.")
            return

        files = os.listdir(UPLOADS_FOLDER)
        if not files:
            self.log("No files found in uploads folder.")
            messagebox.showinfo("Uploads History", "No upload files found.")
            return

        history = "\n".join(files)
        self.log("Uploads History:\n" + history)
        messagebox.showinfo("Uploads History", f"Files in uploads:\n{history}")

def main():
    root = tk.Tk()
    app = LauncherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
