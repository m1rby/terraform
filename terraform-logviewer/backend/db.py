# backend/db.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "logs.db"

def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        level TEXT,
        message TEXT,
        tf_req_id TEXT,
        tf_section TEXT,
        raw TEXT
    )
    """)
    cur.execute("CREATE VIRTUAL TABLE IF NOT EXISTS logs_fts USING fts5(message, raw);")
    conn.commit()
    return conn

def insert_log(conn, entry):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO logs (timestamp, level, message, tf_req_id, tf_section, raw) VALUES (?, ?, ?, ?, ?, ?)",
        (entry["timestamp"], entry["level"], entry["message"], entry["tf_req_id"], entry["tf_section"], entry["raw"])
    )
    rowid = cur.lastrowid
    cur.execute("INSERT INTO logs_fts(rowid, message, raw) VALUES (?, ?, ?)", (rowid, entry["message"], entry["raw"]))
    conn.commit()
    return rowid
