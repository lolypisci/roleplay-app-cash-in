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

# Montar carpeta static/
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
    productos: str = Form(...),
    costes: str = Form(...),
    audio: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if audio.content_type.split("/")[0] != "audio":
        raise HTTPException(status_code=400, detail="Must upload audio")

    try:
        productos_list = [p.strip() for p in productos.split(",") if p.strip()]
        costes_list = [float(c.strip()) for c in costes.split(",") if c.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid format in products or costs")

    ext = os.path.splitext(audio.filename)[1] or ".wav"
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", filename)
    with open(path, "wb") as f:
        f.write(await audio.read())

    rp = models.Roleplay(
        comprador=comprador,
        vendedor=vendedor,
        productos=json.dumps(productos_list),
        costes=json.dumps(costes_list),
        audio_filename=filename
    )
    db.add(rp)
    db.commit()
    db.refresh(rp)
    return JSONResponse({"status": "ok", "id": rp.id})

@app.get("/roleplays")
def list_roleplays(db: Session = Depends(get_db)):
    items = db.query(models.Roleplay).all()
    out = []
    for r in items:
        try:
            productos = json.loads(r.productos)
        except:
            productos = []
        try:
            costes = json.loads(r.costes)
        except:
            costes = []
        out.append({
            "id": r.id,
            "comprador": r.comprador,
            "vendedor": r.vendedor,
            "productos": productos,
            "costes": costes,
            "audio_url": f"/audio/{r.audio_filename}",
            "timestamp": r.timestamp.isoformat()
        })
    return out

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    path = os.path.join("uploads", filename)
    if not os.path.isfile(path):
        raise HTTPException(404)
    ext = os.path.splitext(filename)[1].lower()
    media = {
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".mp3": "audio/mpeg"
    }.get(ext, "application/octet-stream")
    return FileResponse(path, media_type=media)

@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")

@app.get("/student")
async def serve_student():
    return FileResponse("static/student.html")
