import hmac
import hashlib


def make_hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_hmac(key: bytes, data: bytes, tag: bytes) -> bool:
    expected = make_hmac(key, data)
    return hmac.compare_digest(expected, tag)