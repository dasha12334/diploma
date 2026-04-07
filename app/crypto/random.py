import secrets
from app.config import SALT_SIZE, NONCE_SIZE, KEY_SIZE


def generate_salt(size: int = SALT_SIZE) -> bytes:
    return secrets.token_bytes(size)


def generate_nonce(size: int = NONCE_SIZE) -> bytes:
    return secrets.token_bytes(size)


def generate_master_key(size: int = KEY_SIZE) -> bytes:
    return secrets.token_bytes(size)