# rolefy_launcher.py

import subprocess
import webbrowser
import time
import sys
import os
import signal
import socket

def is_windows():
    return os.name == 'nt'

def is_port_open(host='127.0.0.1', port=8000):
    # Comprueba si el puerto ya está abierto (es decir backend corriendo)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0

def main():
    backend_script = 'main.py'
    icon_path = 'icon.ico'  # Asumiendo que está en la misma carpeta que launcher.py
    backend_url = 'http://127.0.0.1:8000'

    if not os.path.isfile(backend_script):
        print(f"Error: No se encontró el archivo backend '{backend_script}'.")
        sys.exit(1)
    if not os.path.isfile(icon_path):
        print(f"Advertencia: No se encontró el icono '{icon_path}', el ejecutable se generará sin icono.")

    backend_process = None

    try:
        if is_port_open():
            print("Backend ya está corriendo en el puerto 8000, no se inicia de nuevo.")
        else:
            print("Iniciando backend...")
            if is_windows():
                backend_process = subprocess.Popen(['python', backend_script], shell=True)
            else:
                backend_process = subprocess.Popen(['python3', backend_script])
            # Esperar un poco a que arranque
            time.sleep(4)

            if not is_port_open():
                print("Error: No se pudo iniciar el backend correctamente.")
                if backend_process:
                    backend_process.terminate()
                sys.exit(1)

        print(f"Abriendo navegador en {backend_url}...")
        webbrowser.open(backend_url)

        if backend_process:
            backend_process.wait()
        else:
            # Si backend ya estaba corriendo, solo esperamos Ctrl+C
            print("Presiona Ctrl+C para salir.")
            while True:
                time.sleep(1)

    except KeyboardInterrupt:
        print("Terminando backend y saliendo...")
        if backend_process:
            if is_windows():
                backend_process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                backend_process.terminate()
            backend_process.wait()
        sys.exit(0)

if __name__ == "__main__":
    main()
