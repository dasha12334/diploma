# app/services/auth_service.py

from app.storage.repository import get_user_by_username
from app.crypto.password import verify_password


def authenticate(username: str, password: str):
    """Аутентификация пользователя"""
    user = get_user_by_username(username)

    if not user:
        return None

    # Проверяем пароль
    if not verify_password(password, user["password_hash"]):
        return None

    return user