# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from db import init_db, insert_log
from parsers import parse_json_lines

app = FastAPI(title="Terraform LogViewer - Backend")
conn = init_db()

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    entries = parse_json_lines(text)
    inserted = 0
    for e in entries:
        insert_log(conn, e)
        inserted += 1
    return {"status": "ok", "entries_detected": len(entries), "inserted": inserted}
