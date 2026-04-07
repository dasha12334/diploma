import json
from datetime import datetime

from app.crypto.aead import encrypt, decrypt
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
                "encrypted_data_key": item["encrypted_data_key"].hex(),
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
    encrypted = encrypt(raw, master_key, associated_data=vault_name.encode("utf-8"))

    add_audit_event(vault_id, "export_vault", f"Vault '{vault_name}' exported")
    return encrypted


def import_vault(vault_id: int, vault_name: str, master_key: bytes, encrypted_payload: bytes) -> None:
    raw = decrypt(encrypted_payload, master_key, associated_data=vault_name.encode("utf-8"))
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