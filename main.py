import os
import json
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models

def log_working_dir():
    print(f"[Startup] Working directory: {os.getcwd()}")

app = FastAPI(on_startup=[log_working_dir])

# Crear tablas si no existen
models.Base.metadata.create_all(bind=engine)

# Montar carpeta estática
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload")
async def upload_roleplay(
    comprador: str = Form(...),
    vendedor: str = Form(...),
    productos_json: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if audio.content_type.split("/")[0] != "audio":
        raise HTTPException(status_code=400, detail="Debe subir un archivo de audio")
    ext = os.path.splitext(audio.filename)[1] or ".wav"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    with open(file_path, "wb") as f:
        content = await audio.read()
        f.write(content)
    rp = models.Roleplay(
        comprador=comprador,
        vendedor=vendedor,
        productos=productos_json,
        audio_filename=filename
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return JSONResponse({"status": "ok", "id": rp.id})

@app.get("/roleplays")
def list_roleplays(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(models.Roleplay).offset(skip).limit(limit).all()
    result = []
    for r in items:
        try:
            productos = json.loads(r.productos)
        except:
            productos = []
        result.append({
            "id": r.id,
            "comprador": r.comprador,
            "vendedor": r.vendedor,
            "productos": productos,
            "audio_url": f"/audio/{r.audio_filename}",
            "timestamp": r.timestamp.isoformat()
        })
    return result

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = os.path.join("uploads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404)
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".wav":
        media_type = "audio/wav"
    elif ext == ".webm":
        media_type = "audio/webm"
    elif ext == ".mp3":
        media_type = "audio/mpeg"
    else:
        media_type = "application/octet-stream"
    return FileResponse(file_path, media_type=media_type)

@app.get("/")
async def serve_index():
    file_path = os.path.join("static", "index.html")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(file_path)

@app.get("/student")
async def serve_student():
    file_path = os.path.join("static", "student.html")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="student.html not found")
    return FileResponse(file_path)
