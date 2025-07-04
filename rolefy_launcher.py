import subprocess
import webbrowser
import time
import sys
import os
import signal

def is_windows():
    return os.name == 'nt'

def main():
    backend_script = 'main.py'
    icon_path = 'icon.ico'  # Asumiendo que está en la misma carpeta que launcher.py

    if not os.path.isfile(backend_script):
        print(f"Error: No se encontró el archivo backend '{backend_script}'.")
        sys.exit(1)
    if not os.path.isfile(icon_path):
        print(f"Advertencia: No se encontró el icono '{icon_path}', el ejecutable se generará sin icono.")

    # Ejecutar backend en proceso separado
    if is_windows():
        backend_process = subprocess.Popen(['python', backend_script], shell=True)
    else:
        backend_process = subprocess.Popen(['python3', backend_script])

    time.sleep(3)  # Esperar a que el backend inicie

    # Abrir la app en navegador apuntando al backend local
    webbrowser.open('http://127.0.0.1:8000')

    try:
        backend_process.wait()
    except KeyboardInterrupt:
        print("Terminando backend y saliendo...")
        if is_windows():
            backend_process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            backend_process.terminate()
        backend_process.wait()

if __name__ == "__main__":
    main()
