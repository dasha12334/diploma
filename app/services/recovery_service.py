# app/services/recovery_service.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import secrets
from datetime import datetime
from typing import Optional

from app.config import KEY_SIZE
from app.crypto.aead import encrypt, decrypt
from app.crypto.kdf import derive_key
from app.crypto.random import generate_salt
from app.storage.repository import get_connection, get_vault_by_id, add_audit_event


class RecoveryService:
    """Сервис для восстановления доступа к vault"""

    @staticmethod
    def setup_master_password(vault_id: int, master_key: bytes, recovery_password: str) -> str:
        """
        Настраивает мастер-пароль для восстановления.
        Возвращает recovery_token для восстановления.
        """
        salt = generate_salt()
        recovery_key = derive_key(recovery_password, salt)

        # Шифруем мастер-ключ
        encrypted_master_key = encrypt(master_key, recovery_key)

        # Генерируем токен восстановления (включаем соль в токен)
        recovery_token = secrets.token_hex(16)

        # Сохраняем соль вместе с токеном для восстановления
        full_token = f"{vault_id}:{salt.hex()}:{recovery_token}"

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO recovery_keys (vault_id, encrypted_master_key, recovery_key_hint, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (vault_id, encrypted_master_key, recovery_token[:8], datetime.utcnow().isoformat())
        )

        conn.commit()
        conn.close()

        add_audit_event(vault_id, "setup_recovery", "Master password recovery set up")

        # Возвращаем полный токен для сохранения пользователем
        return full_token

    @staticmethod
    def recover_with_master_password(vault_id: int, recovery_password: str, recovery_token: str) -> Optional[bytes]:
        """
        Восстанавливает мастер-ключ с помощью мастер-пароля.
        """
        conn = get_connection()
        cursor = conn.cursor()

        # Извлекаем соль из токена
        parts = recovery_token.split(":")
        if len(parts) >= 3:
            token_vault_id = int(parts[0])
            salt_hex = parts[1]
            token_hint = parts[2][:8] if len(parts[2]) >= 8 else parts[2]

            # Проверяем, что vault_id совпадает
            if token_vault_id != vault_id:
                conn.close()
                return None
        else:
            # Старый формат токена (без соли)
            token_hint = recovery_token[:8]
            salt_hex = None

        cursor.execute(
            """
            SELECT encrypted_master_key
            FROM recovery_keys
            WHERE vault_id = ?
              AND recovery_key_hint = ?
            """,
            (vault_id, token_hint)
        )

        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        try:
            # Используем соль из токена или генерируем новую
            if salt_hex:
                salt = bytes.fromhex(salt_hex)
            else:
                # Для обратной совместимости со старыми токенами
                salt = generate_salt()

            recovery_key = derive_key(recovery_password, salt)
            master_key = decrypt(row["encrypted_master_key"], recovery_key)

            # Логируем успешное восстановление
            RecoveryService._log_recovery(vault_id, True, "master_password")

            add_audit_event(vault_id, "recovery_success", "Recovered with master password")

            return master_key
        except Exception as e:
            print(f"Recovery error: {e}")
            pass

        RecoveryService._log_recovery(vault_id, False, "master_password")
        return None

    @staticmethod
    def _log_recovery(vault_id: int, success: bool, method: str, details: str = None):
        """Логирует попытку восстановления"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO recovery_log (vault_id, recovery_time, success, method, details)
            VALUES (?, ?, ?, ?, ?)
            """,
            (vault_id, datetime.utcnow().isoformat(), success, method, details)
        )

        conn.commit()
        conn.close()

    @staticmethod
    def check_recovery_status(vault_id: int) -> dict:
        """Проверяет, настроено ли восстановление"""
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) as count FROM recovery_keys WHERE vault_id = ?",
            (vault_id,)
        )
        row = cursor.fetchone()
        conn.close()

        return {
            "has_recovery": row["count"] > 0,
            "recovery_methods": ["master_password"] if row["count"] > 0 else []
        }