# app/crypto/password.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import hashlib
import os
import hmac


def hash_password(password: str, salt: bytes | None = None) -> bytes:
    """Хеширует пароль с солью используя PBKDF2"""
    if salt is None:
        salt = os.urandom(16)

    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000,  # итераций
        dklen=32  # 256 бит
    )

    return salt + pwd_hash


def verify_password(password: str, stored: bytes) -> bool:
    """
    Проверяет пароль используя безопасное сравнение.
    Защищено от timing attacks через hmac.compare_digest.
    """
    salt = stored[:16]
    stored_hash = stored[16:]

    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000,
        dklen=32
    )

    # 🔥 Используем безопасное сравнение
    return hmac.compare_digest(pwd_hash, stored_hash)