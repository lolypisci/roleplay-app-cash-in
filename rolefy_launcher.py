import subprocess, os, webbrowser, datetime, shutil, requests
from dotenv import load_dotenv
load_dotenv()
RAILWAY_TOKEN=os.getenv("RAILWAY_TOKEN"); PROJECT_ID=os.getenv("PROJECT_ID")

def open_student_app():
    exe="student_app.exe"
    if os.path.exists(exe): os.startfile(exe); return
    print("student_app.exe not found.")

def open_teacher_view():
    webbrowser.open("http://127.0.0.1:8000/")

def make_backup():
    ts=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("updates",exist_ok=True)
    zipf=f"updates/backup_{ts}.zip"
    shutil.make_archive(zipf.replace('.zip',''),'zip',root_dir='.',base_dir='uploads')
    print("Backup created:",zipf)

def restart_railway():
    url=f"https://backboard.railway.app/api/v1/projects/{PROJECT_ID}/restart"
    h={"Authorization":f"Bearer {RAILWAY_TOKEN}"}
    r=requests.post(url,headers=h)
    print("Status:",r.status_code)

if __name__=="__main__":
    # Ejemplo de uso:
    open_teacher_view()
