from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.config import KDF_ITERATIONS, KEY_SIZE


def derive_key(password: str, salt: bytes, iterations: int = KDF_ITERATIONS) -> bytes:
    if not password:
        raise ValueError("Password must not be empty")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def verify_password(password: str, salt: bytes, expected_key: bytes, iterations: int = KDF_ITERATIONS) -> bool:
    try:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_SIZE,
            salt=salt,
            iterations=iterations,
        )
        kdf.verify(password.encode("utf-8"), expected_key)
        return True
    except Exception:
        return False