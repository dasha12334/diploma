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
    """Инициализация базы данных."""
    conn = get_connection()
    cursor = conn.cursor()

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()