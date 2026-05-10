# app/services/backup_shares_service.py

import json
import os
from datetime import datetime
from typing import List, Tuple
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import KEY_SIZE
from app.crypto.random import generate_nonce
from app.storage.repository import get_shares, get_vault_by_id
from app.utils.serialization import deserialize_share, serialize_share


class SharesBackupService:
    """Сервис для резервного копирования долей Шамира"""

    @staticmethod
    def export_shares(vault_id: int, output_dir: str, password: str = None) -> List[str]:
        """
        Экспортирует доли в отдельные файлы.
        Если указан пароль, доли шифруются.

        Returns:
            Список созданных файлов
        """
        vault = get_vault_by_id(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        shares = get_shares(vault_id)
        if not shares:
            raise ValueError("No shares found")

        created_files = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for share in shares:
            share_index = share["share_index"]
            share_payload = share["share_payload"]

            # Расшифровываем долю если нужно? Нет, экспортируем как есть

            # Если указан пароль, шифруем долю
            if password:
                from app.crypto.kdf import derive_key
                from app.crypto.aead import encrypt

                salt = os.urandom(16)
                key = derive_key(password, salt)
                encrypted_share = encrypt(share_payload, key, associated_data=f"share_{share_index}".encode())

                export_data = {
                    "encrypted": True,
                    "vault_name": vault["name"],
                    "share_index": share_index,
                    "salt": salt.hex(),
                    "data": encrypted_share.hex(),
                    "exported_at": timestamp
                }
            else:
                export_data = {
                    "encrypted": False,
                    "vault_name": vault["name"],
                    "share_index": share_index,
                    "data": share_payload.hex(),
                    "exported_at": timestamp
                }

            # Сохраняем файл
            filename = f"share_{vault['name']}_{share_index}_{timestamp}.share"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            created_files.append(filepath)

        return created_files

    @staticmethod
    def import_shares(vault_id: int, share_files: List[str], password: str = None) -> int:
        """
        Импортирует доли из файлов.

        Returns:
            Количество успешно импортированных долей
        """
        from app.storage.repository import add_share

        vault = get_vault_by_id(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        imported = 0

        for filepath in share_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Проверяем, что доля для этого vault
                if data["vault_name"] != vault["name"]:
                    continue

                # Расшифровываем если нужно
                if data.get("encrypted", False):
                    if not password:
                        continue
                    from app.crypto.kdf import derive_key
                    from app.crypto.aead import decrypt

                    salt = bytes.fromhex(data["salt"])
                    key = derive_key(password, salt)
                    share_payload = decrypt(
                        bytes.fromhex(data["data"]),
                        key,
                        associated_data=f"share_{data['share_index']}".encode()
                    )
                else:
                    share_payload = bytes.fromhex(data["data"])

                # Сохраняем долю
                add_share(vault_id, data["share_index"], share_payload)
                imported += 1

            except Exception as e:
                print(f"Failed to import {filepath}: {e}")
                continue

        return imported

    @staticmethod
    def verify_shares_backup(vault_id: int, backup_dir: str) -> dict:
        """Проверяет, что все доли есть в бэкапе"""
        vault = get_vault_by_id(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        shares = get_shares(vault_id)
        expected_indices = {s["share_index"] for s in shares}

        # Ищем файлы бэкапов
        backup_indices = set()
        for filename in os.listdir(backup_dir):
            if filename.startswith(f"share_{vault['name']}_") and filename.endswith(".share"):
                # Извлекаем индекс из имени файла
                parts = filename.split("_")
                if len(parts) >= 3:
                    try:
                        idx = int(parts[2])
                        backup_indices.add(idx)
                    except ValueError:
                        pass

        return {
            "vault_id": vault_id,
            "vault_name": vault["name"],
            "total_shares": len(expected_indices),
            "backup_shares": len(backup_indices),
            "missing_indices": list(expected_indices - backup_indices),
            "extra_indices": list(backup_indices - expected_indices),
            "complete": expected_indices == backup_indices
        }

    @staticmethod
    def restore_from_backup(vault_id: int, backup_dir: str, password: str = None) -> bool:
        """Восстанавливает все доли из бэкапа"""
        vault = get_vault_by_id(vault_id)
        if not vault:
            raise ValueError(f"Vault {vault_id} not found")

        # Находим все файлы бэкапов для этого vault
        share_files = []
        for filename in os.listdir(backup_dir):
            if filename.startswith(f"share_{vault['name']}_") and filename.endswith(".share"):
                share_files.append(os.path.join(backup_dir, filename))

        if not share_files:
            return False

        imported = SharesBackupService.import_shares(vault_id, share_files, password)
        return imported > 0