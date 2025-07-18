import os
import json
import uuid
import traceback
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
from datetime import datetime

app = FastAPI()

models.Base.metadata.create_all(bind=engine)

# Montar carpeta static para servir logo, iconos, CSS, JS, etc.
app.mount("/static", StaticFiles(directory="static"), name="static")
# Montar carpeta uploads para servir audios
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


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

    ext = os.path.splitext(audio.filename)[1] or ".wav"
    filename = f"{uuid.uuid4().hex}{ext}"
    os.makedirs("uploads", exist_ok=True)
    path = os.path.join("uploads", filename)
    with open(path, "wb") as f:
        f.write(await audio.read())

    rp = models.Roleplay(
        comprador=comprador,
        vendedor=vendedor,
        productos=productos,
        costes=costes,
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
            "audio_url": f"/uploads/{r.audio_filename}",
            "timestamp": r.timestamp.isoformat(),
            "feedback": r.feedback or "",
            "nota": r.nota or ""
        })
    return out


@app.post("/update_feedback")
async def update_feedback(request: Request, db: Session = Depends(get_db)):
    try:
        data = await request.json()
        roleplay_id = data.get("id")
        feedback = data.get("feedback", None)
        nota = data.get("nota", None)

        rp = db.query(models.Roleplay).filter(models.Roleplay.id == roleplay_id).first()

        if rp:
            if feedback is not None:
                rp.feedback = feedback
            if nota is not None:
                rp.nota = nota
            db.commit()
            return {"status": "ok"}

        return {"status": "error", "message": "Roleplay not found"}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    path = os.path.join("uploads", filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    ext = os.path.splitext(filename)[1].lower()
    media = {
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".mp3": "audio/mpeg"
    }.get(ext, "application/octet-stream")
    return FileResponse(path, media_type=media)


@app.get("/uploads")
def list_uploads():
    UPLOADS_FOLDER = "uploads"
    if not os.path.isdir(UPLOADS_FOLDER):
        return JSONResponse(content=[], status_code=200)
    files = []
    for fname in os.listdir(UPLOADS_FOLDER):
        if fname.lower().endswith((".wav", ".webm", ".mp3")):
            path = os.path.join(UPLOADS_FOLDER, fname)
            files.append({
                "filename": fname,
                "timestamp": datetime.fromtimestamp(os.path.getmtime(path)).isoformat()
            })
    files.sort(key=lambda x: x["timestamp"], reverse=True)
    return JSONResponse(content=files)


@app.get("/")
async def serve_index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
