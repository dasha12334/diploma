import json

from app.crypto.aead import encrypt, decrypt
from app.crypto.random import generate_master_key
from app.storage.repository import (
    add_secret,
    get_secret_by_id,
    add_audit_event,
    delete_secret,
    update_secret,
)


def remove_secret(secret_id: int):
    delete_secret(secret_id)


def edit_secret(secret_id: int, master_key: bytes, login, password, url, note):
    raw = _pack_secret_data(login, password, url, note)

    # новый data_key
    data_key = generate_master_key()

    encrypted_secret = encrypt(raw, data_key)
    encrypted_data_key = encrypt(data_key, master_key)

    update_secret(secret_id, encrypted_secret, encrypted_data_key, login, url, note)


def _pack_secret_data(login, password, url, note) -> bytes:
    payload = {
        "login": login,
        "password": password,
        "url": url,
        "note": note,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _unpack_secret_data(data: bytes) -> dict:
    return json.loads(data.decode("utf-8"))


def create_secret(
    vault_id: int,
    master_key: bytes,
    name: str,
    login: str | None,
    password: str,
    url: str | None = None,
    note: str | None = None,
) -> int:
    if not name:
        raise ValueError("Secret name must not be empty")
    if not password:
        raise ValueError("Password must not be empty")

    raw = _pack_secret_data(login, password, url, note)

    # 🔥 новый ключ на каждый секрет
    data_key = generate_master_key()

    encrypted_secret = encrypt(raw, data_key)
    encrypted_data_key = encrypt(data_key, master_key)

    secret_id = add_secret(
        vault_id=vault_id,
        name=name,
        login=login,
        url=url,
        note=note,
        encrypted_secret=encrypted_secret,
        encrypted_data_key=encrypted_data_key,
    )

    add_audit_event(vault_id, "add_secret", f"Secret '{name}' added")
    return secret_id


def read_secret(secret_id: int, master_key: bytes) -> dict:
    row = get_secret_by_id(secret_id)
    if not row:
        raise ValueError("Secret not found")

    vault_id = row["vault_id"]

    # 1. достаём data_key
    data_key = decrypt(row["encrypted_data_key"], master_key)

    # 2. расшифровываем секрет
    raw = decrypt(row["encrypted_secret"], data_key)

    data = _unpack_secret_data(raw)

    return {
        "id": row["id"],
        "name": row["name"],
        "login": data.get("login"),
        "password": data.get("password"),
        "url": data.get("url"),
        "note": data.get("note"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }