import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "logs.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("Схема таблицы logs:")
for row in cur.execute("PRAGMA table_info(logs)"):
    print(row)

print("\nПримеры записей:")
for row in cur.execute("SELECT id, timestamp, level, message FROM logs LIMIT 5"):
    print(row)
