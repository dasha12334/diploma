# app/services/user_service.py

from app.storage.repository import create_user, get_user_by_username


def register_user(username: str, password: str):
    """Регистрация нового пользователя"""
    if not username or not password:
        raise ValueError("Username and password cannot be empty")

    # Проверяем, не существует ли уже пользователь
    existing_user = get_user_by_username(username)
    if existing_user:
        raise ValueError(f"User '{username}' already exists")

    create_user(username, password)


def get_user(username: str):
    """Получить пользователя по имени"""
    return get_user_by_username(username)