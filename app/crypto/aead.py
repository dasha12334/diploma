from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import NONCE_SIZE
from app.crypto.random import generate_nonce


def encrypt(plaintext: bytes, key: bytes, associated_data: bytes | None = None) -> bytes:
    if associated_data is None:
        associated_data = b""

    nonce = generate_nonce(NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)

    return nonce + ciphertext


def decrypt(token: bytes, key: bytes, associated_data: bytes | None = None) -> bytes:
    if associated_data is None:
        associated_data = b""

    nonce = token[:NONCE_SIZE]
    ciphertext = token[NONCE_SIZE:]

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data)