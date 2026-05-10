# app/storage/repository.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

from datetime import datetime
from typing import Optional, List

from app.storage.db import get_connection
from app.crypto.password import hash_password, verify_password


def create_vault_meta(name: str, n: int, k: int, password_salt: bytes, password_verifier: bytes) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO vault_meta (name, created_at, n, k, password_salt, password_verifier, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (name, datetime.utcnow().isoformat(), n, k, password_salt, password_verifier, "locked"),
    )

    vault_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return vault_id


def get_vault_by_name(name: str) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vault_meta WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None

# app/storage/repository.py - добавьте эту функцию после get_vault_by_name

def get_vault_by_id(vault_id: int) -> Optional[dict]:
    """Получает vault по ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM vault_meta WHERE id = ?", (vault_id,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def add_share(vault_id: int, share_index: int, share_payload: bytes) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO shares (vault_id, share_index, share_payload, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (vault_id, share_index, share_payload, datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def get_shares(vault_id: int) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT share_index, share_payload
        FROM shares
        WHERE vault_id = ?
        ORDER BY share_index ASC
        """,
        (vault_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def add_secret(
        vault_id: int,
        name: str,
        url: str | None,
        note: str | None,
        encrypted_secret: bytes,
        encrypted_data_key: bytes,
        integrity_hash: str = None,  # 🔥 НОВЫЙ ПАРАМЕТР
) -> int:
    """Сохраняет секрет в БД с хешем целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        INSERT INTO secrets (vault_id, name, url, note, 
                             encrypted_secret, encrypted_data_key, 
                             integrity_hash, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (vault_id, name, url, note,
         encrypted_secret, encrypted_data_key,
         integrity_hash, now, now),
    )

    secret_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return secret_id


def update_secret(
    secret_id: int,
    encrypted_secret: bytes,
    encrypted_data_key: bytes,
    url: str | None,
    note: str | None,
    integrity_hash: str = None,  # 🔥 НОВЫЙ ПАРАМЕТР
) -> None:
    """Обновляет секрет в БД с хешем целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        UPDATE secrets
        SET encrypted_secret = ?,
            encrypted_data_key = ?,
            url = ?,
            note = ?,
            integrity_hash = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (encrypted_secret, encrypted_data_key, url, note,
         integrity_hash, now, secret_id),
    )

    conn.commit()
    conn.close()


def get_secrets(vault_id: int) -> List[dict]:
    """Получает все секреты vault с хешами целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, vault_id, name, url, note, 
               encrypted_secret, encrypted_data_key, 
               integrity_hash, created_at, updated_at
        FROM secrets
        WHERE vault_id = ?
        ORDER BY id ASC
        """,
        (vault_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_secret_by_id(secret_id: int) -> Optional[dict]:
    """Получает секрет по ID с хешем целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, vault_id, name, url, note, 
               encrypted_secret, encrypted_data_key,
               integrity_hash, created_at, updated_at
        FROM secrets
        WHERE id = ?
        """,
        (secret_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def add_audit_event(vault_id: int | None, event_type: str, details: str | None = None) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO audit_log (vault_id, event_type, details, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (vault_id, event_type, details, datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def delete_secret(secret_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM secrets WHERE id = ?", (secret_id,))

    conn.commit()
    conn.close()


# app/storage/repository.py - ИСПРАВЛЯЕМ update_secret


def update_failed_attempt(vault_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE vault_meta
        SET failed_attempts     = failed_attempts + 1,
            last_failed_attempt = ?
        WHERE id = ?
        """,
        (datetime.utcnow().isoformat(), vault_id),
    )

    conn.commit()
    conn.close()


def reset_failed_attempts(vault_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE vault_meta
        SET failed_attempts     = 0,
            last_failed_attempt = NULL
        WHERE id = ?
        """,
        (vault_id,),
    )

    conn.commit()
    conn.close()


# ========== ПОЛЬЗОВАТЕЛИ И ПРАВА ДОСТУПА ==========

def create_user(username: str, password: str):
    """Создаёт нового пользователя с хешированным паролем"""
    conn = get_connection()
    cursor = conn.cursor()

    # Используем функцию hash_password из crypto.password
    password_hash = hash_password(password)

    cursor.execute(
        """
        INSERT INTO users (username, password_hash, created_at)
        VALUES (?, ?, ?)
        """,
        (username, password_hash, datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    """Получает пользователя по имени"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[dict]:
    """Получает пользователя по ID"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, password_hash, created_at FROM users WHERE id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_all_users() -> List[dict]:
    """Возвращает список всех пользователей"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, username, created_at FROM users ORDER BY id")
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def grant_user_access(user_id: int, vault_id: int, role: str) -> None:
    """Назначает пользователю роль в хранилище"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO user_vault_access (user_id, vault_id, role, granted_at)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, vault_id, role, datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def get_user_role(user_id: int, vault_id: int) -> Optional[str]:
    """Получает роль пользователя в хранилище"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT role
        FROM user_vault_access
        WHERE user_id = ?
          AND vault_id = ?
        """,
        (user_id, vault_id),
    )
    row = cursor.fetchone()
    conn.close()

    return row["role"] if row else None


def get_vault_users(vault_id: int) -> List[dict]:
    """Возвращает список пользователей хранилища с их ролями"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT u.id, u.username, uva.role, uva.granted_at
        FROM users u
                 JOIN user_vault_access uva ON u.id = uva.user_id
        WHERE uva.vault_id = ?
        ORDER BY uva.role, u.username
        """,
        (vault_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

# Добавьте в app/storage/repository.py:

# app/storage/repository.py - ПРОВЕРЬТЕ save_secret_version

def save_secret_version(
    secret_id: int,
    version: int,
    encrypted_secret: bytes,
    encrypted_data_key: bytes,
    url: str | None,
    note: str | None,
) -> None:
    """Сохраняет версию секрета"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO secret_versions (
            secret_id, version, encrypted_secret, encrypted_data_key, 
            url, note, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (secret_id, version, encrypted_secret, encrypted_data_key,
         url, note, datetime.utcnow().isoformat()),
    )

    conn.commit()
    conn.close()


def get_secret_version(secret_id: int, version: int) -> Optional[dict]:
    """Получает конкретную версию секрета"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM secret_versions
        WHERE secret_id = ? AND version = ?
        """,
        (secret_id, version),
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_secret_versions(secret_id: int) -> List[dict]:
    """Получает все версии секрета"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, version, url, note, created_at
        FROM secret_versions
        WHERE secret_id = ?
        ORDER BY version DESC
        """,
        (secret_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_latest_version(secret_id: int) -> int:
    """Получает номер последней версии секрета"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COALESCE(MAX(version), 0) as max_version
        FROM secret_versions
        WHERE secret_id = ?
        """,
        (secret_id,),
    )
    row = cursor.fetchone()
    conn.close()

    return row["max_version"] if row else 0


def cleanup_old_versions(secret_id: int, keep_versions: int = 10) -> None:
    """Удаляет старые версии, оставляя только последние keep_versions"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM secret_versions
        WHERE secret_id = ? AND version <= (
            SELECT MIN(version) FROM (
                SELECT version FROM secret_versions
                WHERE secret_id = ?
                ORDER BY version DESC
                LIMIT ? OFFSET ?
            )
        )
        """,
        (secret_id, secret_id, keep_versions, keep_versions),
    )

    conn.commit()
    conn.close()


# app/storage/repository.py - добавим функции поиска

def search_secrets(vault_id: int, search_term: str) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT id, vault_id, name, url, note,
               encrypted_secret, encrypted_data_key,
               created_at, updated_at
        FROM secrets
        WHERE vault_id = ?
          AND (
            LOWER(name) LIKE LOWER(?)
            OR LOWER(url) LIKE LOWER(?)
            OR LOWER(note) LIKE LOWER(?)
          )
        ORDER BY name ASC
    """
    search_pattern = f"%{search_term}%"
    cursor.execute(query, (vault_id, search_pattern, search_pattern, search_pattern))  # всего 4 значения
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_secrets_by_category(vault_id: int, category: str = None) -> List[dict]:
    """
    Получает секреты с группировкой по категориям (по первой букве или домену).
    """
    conn = get_connection()
    cursor = conn.cursor()

    if category:
        # Фильтрация по первой букве
        cursor.execute(
            """
            SELECT id,
                   vault_id,
                   name,
                   url,
                   note,
                   encrypted_secret,
                   encrypted_data_key,
                   created_at,
                   updated_at
            FROM secrets
            WHERE vault_id = ?
              AND LOWER(name) LIKE LOWER(?)
            ORDER BY name ASC
            """,
            (vault_id, f"{category}%"),
        )
    else:
        cursor.execute(
            """
            SELECT id,
                   vault_id,
                   name,
                   url,
                   note,
                   encrypted_secret,
                   encrypted_data_key,
                   created_at,
                   updated_at
            FROM secrets
            WHERE vault_id = ?
            ORDER BY name ASC
            """,
            (vault_id,),
        )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_secret_categories(vault_id: int) -> List[str]:
    """Получает список уникальных первых букв названий секретов"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DISTINCT UPPER(SUBSTR(name, 1, 1)) as letter
        FROM secrets
        WHERE vault_id = ?
          AND name != ''
        ORDER BY letter ASC
        """,
        (vault_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [row["letter"] for row in rows if row["letter"]]


# app/storage/repository.py - добавить функции

def update_secret_integrity(secret_id: int, integrity_hash: str) -> None:
    """Обновляет хеш целостности секрета"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE secrets SET integrity_hash = ? WHERE id = ?",
        (integrity_hash, secret_id)
    )

    conn.commit()
    conn.close()


def log_integrity_check(vault_id: int, status: str, issues_count: int, details: str = None) -> None:
    """Логирует проверку целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO integrity_log (vault_id, check_time, status, issues_count, details)
        VALUES (?, ?, ?, ?, ?)
        """,
        (vault_id, datetime.utcnow().isoformat(), status, issues_count, details)
    )

    conn.commit()
    conn.close()


def get_last_integrity_check(vault_id: int) -> Optional[dict]:
    """Получает последнюю проверку целостности"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM integrity_log
        WHERE vault_id = ?
        ORDER BY check_time DESC LIMIT 1
        """,
        (vault_id,)
    )
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


# app/storage/repository.py - добавьте эту функцию:

def update_vault_password(vault_id: int, new_salt: bytes, new_verifier: bytes) -> None:
    """Обновляет пароль vault (соль и верификатор)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE vault_meta
        SET password_salt     = ?,
            password_verifier = ?
        WHERE id = ?
        """,
        (new_salt, new_verifier, vault_id)
    )

    conn.commit()
    conn.close()

def delete_shares(vault_id: int) -> None:
    """Удаляет все доли vault"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shares WHERE vault_id = ?", (vault_id,))
    conn.commit()
    conn.close()