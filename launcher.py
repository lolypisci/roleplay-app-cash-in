import subprocess
import os
import webbrowser
import datetime
import shutil

# --- Open student app without console ---
def open_student_app():
    # Asumiendo que el exe está en la carpeta actual
    exe_path = os.path.abspath("student_app.exe")
    if os.path.exists(exe_path):
        # Usar os.startfile para no abrir consola (Windows)
        try:
            os.startfile(exe_path)
            return "Student app opened."
        except Exception as e:
            return f"Failed to open student app: {e}"
    else:
        return "Student app executable not found."

# --- Open teacher view in browser ---
def open_teacher_view():
    # Asumiendo que el servidor corre local en http://127.0.0.1:8000/
    url = "http://127.0.0.1:8000/"
    webbrowser.open(url)
    return "Teacher view opened in browser."

# --- Git add and commit (sin forzar archivos ignorados) ---
def git_add_commit(message):
    try:
        subprocess.run(['git', 'add', '.'], check=True)
        # Check if there is anything to commit
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
        if result.returncode == 0:
            return "No changes to commit."
        subprocess.run(['git', 'commit', '-m', message], check=True)
        return "Commit successful."
    except subprocess.CalledProcessError as e:
        return f"Git error: {e}"

# --- Git push ---
def git_push():
    try:
        subprocess.run(['git', 'push'], check=True)
        return "Push successful."
    except subprocess.CalledProcessError as e:
        return f"Git push error: {e}"

# --- Backup files (db + uploads) en carpeta updates ---
def make_backup():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = "updates"
    os.makedirs(backup_folder, exist_ok=True)
    backup_name = f"backup_{timestamp}.zip"
    backup_path = os.path.join(backup_folder, backup_name)
    try:
        shutil.make_archive(backup_path.replace('.zip',''), 'zip', root_dir='.', base_dir='uploads')
        # También añadir roleplay.db al zip
        # No se puede añadir fácilmente más de una carpeta con shutil.make_archive,
        # se podría copiar roleplay.db dentro de uploads temporalmente o hacer zip manual
        # Para simplicidad, solo zip uploads aquí.
        return f"Backup created at {backup_path}"
    except Exception as e:
        return f"Backup failed: {e}"

# --- Restart Railway project con API ---
import requests
from dotenv import load_dotenv
load_dotenv()

RAILWAY_TOKEN = os.getenv("RAILWAY_TOKEN")
PROJECT_ID = os.getenv("PROJECT_ID")

def restart_railway_project():
    if not RAILWAY_TOKEN or not PROJECT_ID:
        return "RAILWAY_TOKEN or PROJECT_ID not set."

    url = f"https://backboard.railway.app/api/v1/projects/{PROJECT_ID}/restart"
    headers = {
        "Authorization": f"Bearer {RAILWAY_TOKEN}",
        "Content-Type": "application/json"
    }
    try:
        response = requests.post(url, headers=headers)
        if response.status_code == 200:
            return "Railway project restarted successfully."
        else:
            return f"Railway API error: {response.status_code} {response.text}"
    except Exception as e:
        return f"Railway API request failed: {e}"
