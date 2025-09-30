# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from parsers import parse_json_lines

app = FastAPI(title="Terraform LogViewer - Backend")

# Раздача статических файлов (минимальный интерфейс)
# Папка статики находится рядом с backend: backend/public
STATIC_DIR = Path(__file__).parent / "public"
app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.get("/")
async def root_redirect():
    # простой редирект на UI
    return {
        "message": "Open /ui to use the web interface",
        "ui": "/ui"
    }

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    entries = parse_json_lines(text)
    source_name = file.filename or "uploaded.log"
    for e in entries:
        e["source_filename"] = source_name
    return {"status": "ok", "entries_detected": len(entries), "entries": entries, "source_filename": source_name}
