"""API FastAPI — Tradução do Instagram.
POST /dublar : arquivo (áudio ou vídeo) -> áudio dublado em PT + metadados
GET  /health : status + modelos
GET  /       : página de teste (upload do navegador)
"""
import os, shutil, uuid
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from app import config, pipeline

app = FastAPI(title="Tradução do Instagram")

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

_last = {}  # job -> paths


@app.get("/", response_class=HTMLResponse)
def index():
    p = os.path.join("static", "index.html")
    if os.path.exists(p):
        return HTMLResponse(open(p, encoding="utf-8").read())
    return HTMLResponse("<h1>Tradução do Instagram</h1><p>API no ar. POST /dublar</p>")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "whisper": {"model": config.WHISPER_MODEL, "device": config.WHISPER_DEVICE,
                    "compute": config.WHISPER_COMPUTE},
        "ollama": {"url": config.OLLAMA_URL, "model": config.OLLAMA_MODEL},
    }


@app.post("/dublar")
async def dublar(file: UploadFile = File(...), formato: str = "mp3"):
    ext = os.path.splitext(file.filename or "")[1] or ".bin"
    src = os.path.join(config.TMP_DIR, f"up_{uuid.uuid4().hex[:8]}{ext}")
    with open(src, "wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        res = pipeline.process(src)
    except Exception as e:
        raise HTTPException(500, f"falha no processamento: {e}")
    finally:
        if os.path.exists(src):
            os.remove(src)
    if "error" in res:
        return JSONResponse(res, status_code=422)
    _last[res["job"]] = res
    resp = {k: v for k, v in res.items() if k not in ("audio_wav", "audio_mp3")}
    resp["audio_url"] = f"/audio/{res['job']}?fmt={formato}"
    return resp


@app.get("/audio/{job}")
def audio(job: str, fmt: str = "mp3"):
    res = _last.get(job)
    if not res:
        raise HTTPException(404, "job não encontrado (reprocesse)")
    path = res["audio_mp3"] if fmt == "mp3" else res["audio_wav"]
    if not os.path.exists(path):
        raise HTTPException(404, "áudio expirado")
    media = "audio/mpeg" if fmt == "mp3" else "audio/wav"
    return FileResponse(path, media_type=media, filename=f"dublagem_{job}.{fmt}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
