import os
import sqlite3

from app.utils.paths import ensure_data_dir, get_db_path


def get_connection():
    import sqlite3
    from app.utils.paths import ensure_data_dir, get_db_path

    ensure_data_dir()

    conn = sqlite3.connect(
        get_db_path(),
        timeout=10,  # ждём, если база занята
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    # 🔥 важно
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")

    return conn

def init_db():
    import os

    conn = get_connection()
    cursor = conn.cursor()

    # 🔥 правильный абсолютный путь
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base_dir, "storage", "schema.sql")

    print("INIT DB:", schema_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()