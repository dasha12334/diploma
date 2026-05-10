import hmac
import hashlib
import json
from typing import Dict, Any
from datetime import datetime

def make_hmac(key: bytes, data: bytes) -> bytes:
    return hmac.new(key, data, hashlib.sha256).digest()


def verify_hmac(key: bytes, data: bytes, tag: bytes) -> bool:
    expected = make_hmac(key, data)
    return hmac.compare_digest(expected, tag)


# Новые функции для целостности
def compute_data_hash(data: bytes) -> str:
    """Вычисляет хеш данных для проверки целостности"""
    return hashlib.sha256(data).hexdigest()


def verify_secret_integrity(encrypted_secret: bytes, encrypted_data_key: bytes,
                            stored_hash: str) -> bool:
    """Проверяет целостность зашифрованного секрета"""
    combined = encrypted_secret + encrypted_data_key
    current_hash = compute_data_hash(combined)
    return hmac.compare_digest(current_hash, stored_hash)


class IntegrityChecker:
    """Класс для проверки целостности всех данных vault"""

    def __init__(self, master_key: bytes):
        self.master_key = master_key
        self.integrity_log = []

    def check_vault_integrity(self, vault_id: int) -> Dict[str, Any]:
        """Проверяет целостность всего vault"""
        from app.storage.repository import get_secrets, get_shares

        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "vault_id": vault_id,
            "status": "ok",
            "issues": [],
            "checked": {
                "secrets": 0,
                "shares": 0,
                "metadata": False
            }
        }

        # Проверяем секреты
        try:
            secrets = get_secrets(vault_id)
            for secret in secrets:
                result["checked"]["secrets"] += 1
                # Проверка целостности каждого секрета
                if secret.get("integrity_hash"):
                    if not verify_secret_integrity(
                            secret["encrypted_secret"],
                            secret["encrypted_data_key"],
                            secret["integrity_hash"]
                    ):
                        result["issues"].append({
                            "type": "secret",
                            "id": secret["id"],
                            "name": secret["name"],
                            "issue": "integrity_mismatch"
                        })
                        result["status"] = "corrupted"
        except Exception as e:
            result["issues"].append({"type": "secrets", "error": str(e)})
            result["status"] = "error"

        # Проверяем доли
        try:
            shares = get_shares(vault_id)
            for share in shares:
                result["checked"]["shares"] += 1
                # Проверяем формат доли
                if not isinstance(share["share_payload"], bytes) or len(share["share_payload"]) < 10:
                    result["issues"].append({
                        "type": "share",
                        "index": share["share_index"],
                        "issue": "invalid_format"
                    })
        except Exception as e:
            result["issues"].append({"type": "shares", "error": str(e)})

        return result