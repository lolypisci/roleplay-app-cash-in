# run_server.py
import os
import uvicorn
from pyngrok import ngrok, conf

# ====== CONFIGURACIÓN NGROK ======
NGROK_AUTH_TOKEN = "2ylJTHa36okAH5mbcJGnj7EmBV3_76yLGjCe5z9ShjvtkTB8n"
PORT = 8000
# =================================

conf.get_default().auth_token = NGROK_AUTH_TOKEN

def start_ngrok_tunnel():
    tunnel = ngrok.connect(addr=PORT, proto="http")
    public_url = tunnel.public_url
    print(f"Ngrok tunnel: {public_url} -> http://localhost:{PORT}")
    return public_url

def start_uvicorn():
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)

if __name__ == "__main__":
    print(f"[run_server] Working directory: {os.getcwd()}")
    public_url = start_ngrok_tunnel()
    start_uvicorn()
