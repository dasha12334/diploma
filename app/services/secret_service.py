# app/services/secret_service.py - ПОЛНАЯ ВЕРСИЯ С ЦЕЛОСТНОСТЬЮ

import json
from typing import Optional, List

from app.crypto.aead import encrypt, decrypt
from app.crypto.random import generate_master_key
from app.crypto.integrity import compute_data_hash, verify_secret_integrity
from app.storage.repository import (
    add_secret,
    get_secret_by_id,
    add_audit_event,
    delete_secret,
    update_secret as db_update_secret,
    save_secret_version,
    get_secret_versions,
    get_secret_version as get_version_by_number,
    get_latest_version,
    cleanup_old_versions,
    search_secrets as db_search_secrets,
    update_secret_integrity,
)
from app.services.access_service import check_access


def _pack_secret_data(password, url, note) -> bytes:
    """Упаковывает данные секрета в JSON"""
    payload = {
        "password": password,
        "url": url or "",
        "note": note or "",
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _unpack_secret_data(data: bytes) -> dict:
    """Распаковывает данные секрета из JSON"""
    return json.loads(data.decode("utf-8"))


def create_secret(
        vault_id: int,
        master_key: bytes,
        user_id: int,
        name: str,
        password: str,
        url: str | None = None,
        note: str | None = None,
) -> int:
    """Создаёт новый секрет с сохранением хеша целостности"""

    # Проверка прав
    if not check_access(user_id, vault_id, "create"):
        raise PermissionError("Access denied")

    if not name:
        raise ValueError("Secret name must not be empty")
    if not password:
        raise ValueError("Password must not be empty")

    # Упаковываем данные
    raw = _pack_secret_data(password, url, note)

    # Генерируем ключ для этого секрета
    data_key = generate_master_key()

    # Шифруем секрет и ключ
    encrypted_secret = encrypt(raw, data_key)
    encrypted_data_key = encrypt(data_key, master_key)

    # 🔥 ВЫЧИСЛЯЕМ ХЕШ ЦЕЛОСТНОСТИ
    integrity_hash = compute_data_hash(encrypted_secret + encrypted_data_key)

    # Сохраняем в БД (нужно обновить add_secret в repository.py)
    secret_id = add_secret(
        vault_id=vault_id,
        name=name,
        url=url,
        note=note,
        encrypted_secret=encrypted_secret,
        encrypted_data_key=encrypted_data_key,
        integrity_hash=integrity_hash,  # 🔥 НОВЫЙ ПАРАМЕТР
    )

    # Сохраняем первую версию
    save_secret_version(
        secret_id=secret_id,
        version=1,
        encrypted_secret=encrypted_secret,
        encrypted_data_key=encrypted_data_key,
        url=url,
        note=note,
    )

    add_audit_event(vault_id, "add_secret", f"Secret '{name}' added (version 1)")

    return secret_id


def update_secret_logic(
        secret_id: int,
        master_key: bytes,
        user_id: int,
        vault_id: int,
        password: str,
        url: str | None,
        note: str | None,
) -> None:
    """Обновляет существующий секрет с сохранением версии и хеша целостности"""

    if not check_access(user_id, vault_id, "update"):
        raise PermissionError("Access denied")

    # Получаем текущий секрет
    current = get_secret_by_id(secret_id)
    if not current:
        raise ValueError("Secret not found")

    # Получаем номер новой версии
    latest_version = get_latest_version(secret_id)
    new_version = latest_version + 1

    # Упаковываем новые данные
    raw = _pack_secret_data(password, url, note)

    # Генерируем новый ключ для секрета
    data_key = generate_master_key()

    # Шифруем
    encrypted_secret = encrypt(raw, data_key)
    encrypted_data_key = encrypt(data_key, master_key)

    # 🔥 ВЫЧИСЛЯЕМ НОВЫЙ ХЕШ ЦЕЛОСТНОСТИ
    integrity_hash = compute_data_hash(encrypted_secret + encrypted_data_key)

    # Обновляем текущую запись (нужно обновить db_update_secret в repository.py)
    db_update_secret(
        secret_id,
        encrypted_secret,
        encrypted_data_key,
        url,
        note,
        integrity_hash,  # 🔥 НОВЫЙ ПАРАМЕТР
    )

    # Сохраняем новую версию
    save_secret_version(
        secret_id=secret_id,
        version=new_version,
        encrypted_secret=encrypted_secret,
        encrypted_data_key=encrypted_data_key,
        url=url,
        note=note,
    )

    # Очищаем старые версии (оставляем последние 10)
    cleanup_old_versions(secret_id, keep_versions=10)

    add_audit_event(
        vault_id,
        "edit_secret",
        f"Secret {secret_id} updated to version {new_version}"
    )


def read_secret(secret_id: int, master_key: bytes, user_id: int, version: Optional[int] = None) -> dict:
    """
    Читает секрет с ПРОВЕРКОЙ ЦЕЛОСТНОСТИ.
    Если version указан, читает конкретную версию.
    Иначе читает текущую версию.
    """

    # Получаем информацию о секрете
    if version is None:
        # Текущая версия
        row = get_secret_by_id(secret_id)
        if not row:
            raise ValueError("Secret not found")

        encrypted_secret = row["encrypted_secret"]
        encrypted_data_key = row["encrypted_data_key"]
        url = row.get("url")
        note = row.get("note")
        stored_hash = row.get("integrity_hash")  # 🔥 ПОЛУЧАЕМ ХЕШ

    else:
        # Конкретная версия
        version_row = get_version_by_number(secret_id, version)
        if not version_row:
            raise ValueError(f"Version {version} not found")

        encrypted_secret = version_row["encrypted_secret"]
        encrypted_data_key = version_row["encrypted_data_key"]
        url = version_row.get("url")
        note = version_row.get("note")
        stored_hash = None  # У версий пока нет хеша, можно добавить позже

        # Получаем метаданные из основной таблицы
        row = get_secret_by_id(secret_id)
        if not row:
            raise ValueError("Secret not found")

    vault_id = row["vault_id"]

    # Проверка прав
    if not check_access(user_id, vault_id, "read"):
        raise PermissionError("Access denied")

    # 🔥 ПРОВЕРКА ЦЕЛОСТНОСТИ ПЕРЕД РАСШИФРОВКОЙ
    if stored_hash:
        if not verify_secret_integrity(encrypted_secret, encrypted_data_key, stored_hash):
            add_audit_event(vault_id, "integrity_check_failed", f"Secret {secret_id} integrity check failed")
            raise ValueError(f"Integrity check failed for secret {secret_id}. Data may be corrupted.")

    # Расшифровываем
    data_key = decrypt(encrypted_data_key, master_key)
    raw = decrypt(encrypted_secret, data_key)
    data = _unpack_secret_data(raw)

    return {
        "id": row["id"],
        "name": row["name"],
        "password": data.get("password"),
        "url": url or data.get("url"),
        "note": note or data.get("note"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"] if version is None else version_row["created_at"],
        "version": version if version is not None else get_latest_version(secret_id),
        "integrity_checked": bool(stored_hash),  # 🔥 ИНФОРМАЦИЯ О ПРОВЕРКЕ
    }


def get_secret_history(secret_id: int, user_id: int) -> List[dict]:
    """Получает историю версий секрета"""

    row = get_secret_by_id(secret_id)
    if not row:
        raise ValueError("Secret not found")

    vault_id = row["vault_id"]

    if not check_access(user_id, vault_id, "read"):
        raise PermissionError("Access denied")

    versions = get_secret_versions(secret_id)

    return [
        {
            "version": v["version"],
            "url": v.get("url", ""),
            "note": v.get("note", ""),
            "created_at": v["created_at"],
        }
        for v in versions
    ]


def rollback_secret(secret_id: int, target_version: int, master_key: bytes, user_id: int, vault_id: int) -> None:
    """Откатывает секрет к указанной версии с сохранением хеша целостности"""

    if not check_access(user_id, vault_id, "update"):
        raise PermissionError("Access denied")

    # Получаем целевую версию
    version_data = get_version_by_number(secret_id, target_version)
    if not version_data:
        raise ValueError(f"Version {target_version} not found")

    # Получаем текущий секрет для имени
    current = get_secret_by_id(secret_id)
    if not current:
        raise ValueError("Secret not found")

    # Расшифровываем данные целевой версии, чтобы получить password
    data_key = decrypt(version_data["encrypted_data_key"], master_key)
    raw = decrypt(version_data["encrypted_secret"], data_key)
    data = _unpack_secret_data(raw)

    # 🔥 ВЫЧИСЛЯЕМ ХЕШ ДЛЯ ВОССТАНАВЛИВАЕМОЙ ВЕРСИИ
    integrity_hash = compute_data_hash(
        version_data["encrypted_secret"] + version_data["encrypted_data_key"]
    )

    # Обновляем секрет данными из старой версии
    db_update_secret(
        secret_id,
        version_data["encrypted_secret"],
        version_data["encrypted_data_key"],
        version_data.get("url"),
        version_data.get("note"),
        integrity_hash,  # 🔥 НОВЫЙ ПАРАМЕТР
    )

    # Сохраняем новую версию (откат)
    latest_version = get_latest_version(secret_id)
    new_version = latest_version + 1

    save_secret_version(
        secret_id=secret_id,
        version=new_version,
        encrypted_secret=version_data["encrypted_secret"],
        encrypted_data_key=version_data["encrypted_data_key"],
        url=version_data.get("url"),
        note=version_data.get("note"),
    )

    add_audit_event(
        vault_id,
        "rollback_secret",
        f"Secret {secret_id} rolled back from version {latest_version} to {target_version} (new version {new_version})"
    )


# Функция для обратной совместимости
def edit_secret(
    secret_id: int,
    master_key: bytes,
    user_id: int,
    vault_id: int,
    password: str,
    url: str | None,
    note: str | None
) -> None:
    """Обновляет секрет (обёртка над update_secret_logic)"""
    update_secret_logic(secret_id, master_key, user_id, vault_id, password, url, note)


def remove_secret(secret_id: int, user_id: int, vault_id: int) -> None:
    """Удаляет секрет"""
    if not check_access(user_id, vault_id, "delete"):
        raise PermissionError("Access denied")

    delete_secret(secret_id)
    add_audit_event(vault_id, "delete_secret", f"Secret {secret_id} deleted")


# ====================== ПОИСК ======================

def search_secrets(vault_id: int, user_id: int, search_term: str) -> List[dict]:
    """
    Поиск секретов по запросу.
    Требует прав на чтение.
    """
    if not check_access(user_id, vault_id, "read"):
        raise PermissionError("Access denied")

    if not search_term or len(search_term) < 2:
        raise ValueError("Поисковый запрос должен содержать минимум 2 символа")

    results = db_search_secrets(vault_id, search_term)

    # Возвращаем только метаданные (без расшифровки)
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "url": s.get("url", ""),
            "created_at": s["created_at"],
            "updated_at": s["updated_at"],
            "has_integrity": bool(s.get("integrity_hash")),  # 🔥 ИНФОРМАЦИЯ О ЦЕЛОСТНОСТИ
        }
        for s in results
    ]