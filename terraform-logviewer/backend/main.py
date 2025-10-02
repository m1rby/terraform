# backend/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from parsers import parse_json_lines
from plugin_manager import plugin_manager, PluginConfig
from typing import List, Dict, Optional
import os

app = FastAPI(title="Terraform LogViewer - Backend")

# CORS для работы с плагинами
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Раздача статических файлов (минимальный интерфейс)
# Папка статики находится рядом с backend: backend/public
STATIC_DIR = Path(__file__).parent / "public"
app.mount("/ui", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

@app.on_event("startup")
async def startup_event():
    """Инициализация плагинов при старте"""
    print("✓ Backend запущен")
    print("✓ Плагинная система готова к подключению плагинов")
    print("   Плагины можно зарегистрировать через UI или API")

@app.on_event("shutdown")
async def shutdown_event():
    """Закрытие соединений с плагинами"""
    plugin_manager.shutdown()

@app.get("/")
async def root_redirect():
    # простой редирект на UI
    return {
        "message": "Open /ui to use the web interface",
        "ui": "/ui",
        "plugins": "/api/plugins"
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

# ============ Plugin API ============

@app.get("/api/plugins")
async def list_plugins():
    """Список всех зарегистрированных плагинов"""
    return {"plugins": plugin_manager.list_plugins()}

@app.post("/api/plugins/register")
async def register_plugin(
    name: str = Body(...),
    address: str = Body(...),
    enabled: bool = Body(True)
):
    """Регистрация нового плагина"""
    config = PluginConfig(name=name, address=address, enabled=enabled)
    plugin_manager.register_plugin(config)
    return {"status": "ok", "message": f"Plugin '{name}' registered"}

@app.post("/api/plugins/{plugin_name}/filter")
async def filter_logs_via_plugin(
    plugin_name: str,
    logs: List[Dict] = Body(...),
    filter_params: Optional[Dict] = Body(None)
):
    """Фильтрация логов через плагин"""
    filtered = plugin_manager.filter_logs(logs, plugin_name, filter_params)
    return {"filtered_logs": filtered, "count": len(filtered)}

@app.post("/api/plugins/{plugin_name}/process")
async def process_logs_via_plugin(
    plugin_name: str,
    logs: List[Dict] = Body(...),
    process_params: Optional[Dict] = Body(None)
):
    """Обработка логов через плагин"""
    processed, metadata = plugin_manager.process_logs(logs, plugin_name, process_params)
    return {"processed_logs": processed, "metadata": metadata, "count": len(processed)}

@app.post("/api/plugins/{plugin_name}/aggregate")
async def aggregate_logs_via_plugin(
    plugin_name: str,
    logs: List[Dict] = Body(...),
    aggregation_type: str = Body("error_grouping"),
    agg_params: Optional[Dict] = Body(None)
):
    """Агрегация логов через плагин"""
    results = plugin_manager.aggregate_logs(logs, plugin_name, aggregation_type, agg_params)
    return {"aggregation_results": results, "count": len(results)}

@app.delete("/api/plugins/{plugin_name}")
async def delete_plugin(plugin_name: str):
    """Удаление плагина"""
    if plugin_name in plugin_manager.plugins:
        # Закрываем соединение
        if plugin_name in plugin_manager.channels:
            plugin_manager.channels[plugin_name].close()
            del plugin_manager.channels[plugin_name]
        if plugin_name in plugin_manager.stubs:
            del plugin_manager.stubs[plugin_name]
        del plugin_manager.plugins[plugin_name]
        return {"status": "ok", "message": f"Plugin '{plugin_name}' deleted"}
    else:
        raise HTTPException(status_code=404, detail="Plugin not found")
