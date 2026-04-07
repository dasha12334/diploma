import os
from app.config import DATA_DIR


def ensure_data_dir():
    """Создаёт папку data, если её нет"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)


def get_db_path():
    """Возвращает путь к базе данных"""
    return os.path.join(DATA_DIR, "vault.db")