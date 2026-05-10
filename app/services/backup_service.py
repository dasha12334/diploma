import json
from datetime import datetime

from app.crypto.aead import encrypt, decrypt
from app.crypto.integrity import make_hmac, verify_hmac
from app.storage.repository import get_vault_by_name, get_secrets, add_secret, add_audit_event


def export_vault(vault_id: int, vault_name: str, master_key: bytes) -> bytes:
    vault = get_vault_by_name(vault_name)
    if not vault:
        raise ValueError("Vault not found")

    secrets = get_secrets(vault_id)

    export_secrets = []
    for item in secrets:
        export_secrets.append(
            {
                "id": item["id"],
                "name": item["name"],
                "login": item.get("login"),
                "url": item.get("url"),
                "note": item.get("note"),
                "encrypted_secret": item["encrypted_secret"].hex(),
                "encrypted_data_key": item["encrypted_data_key"].hex(),  # 🔥 важно
                "created_at": item["created_at"],
                "updated_at": item["updated_at"],
            }
        )

    payload = {
        "vault": {
            "id": vault["id"],
            "name": vault["name"],
            "n": vault["n"],
            "k": vault["k"],
            "created_at": vault["created_at"],
        },
        "secrets": export_secrets,
        "exported_at": datetime.utcnow().isoformat(),
    }

    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # 🔐 шифруем
    encrypted = encrypt(raw, master_key, associated_data=vault_name.encode("utf-8"))

    # 🔐 считаем HMAC
    tag = make_hmac(master_key, encrypted)

    # 📦 итоговый контейнер
    container = {
        "ciphertext": encrypted.hex(),
        "hmac": tag.hex(),
    }

    add_audit_event(vault_id, "export_vault", f"Vault '{vault_name}' exported")

    return json.dumps(container).encode("utf-8")


def import_vault(vault_id: int, vault_name: str, master_key: bytes, data: bytes) -> None:
    container = json.loads(data.decode("utf-8"))

    ciphertext = bytes.fromhex(container["ciphertext"])
    tag = bytes.fromhex(container["hmac"])

    # 🔐 проверяем HMAC ДО расшифровки
    if not verify_hmac(master_key, ciphertext, tag):
        raise ValueError("Backup integrity check failed (HMAC mismatch)")

    # 🔐 расшифровываем
    raw = decrypt(ciphertext, master_key, associated_data=vault_name.encode("utf-8"))
    payload = json.loads(raw.decode("utf-8"))

    secrets = payload.get("secrets", [])

    for item in secrets:
        encrypted_secret = bytes.fromhex(item["encrypted_secret"])
        encrypted_data_key = bytes.fromhex(item["encrypted_data_key"])

        add_secret(
            vault_id=vault_id,
            name=item["name"],
            login=item.get("login"),
            url=item.get("url"),
            note=item.get("note"),
            encrypted_secret=encrypted_secret,
            encrypted_data_key=encrypted_data_key,
        )

    add_audit_event(vault_id, "import_vault", f"Vault '{vault_name}' imported")