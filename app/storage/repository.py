from datetime import datetime
from typing import Optional, List

from app.storage.db import get_connection


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
    login: str | None,
    url: str | None,
    note: str | None,
    encrypted_secret: bytes,
    encrypted_data_key: bytes,
) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        INSERT INTO secrets (vault_id, name, login, url, note, encrypted_secret, encrypted_data_key, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (vault_id, name, login, url, note, encrypted_secret, encrypted_data_key, now, now),
    )

    secret_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return secret_id


def get_secrets(vault_id: int) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, vault_id, name, login, url, note, encrypted_secret, encrypted_data_key, created_at, updated_at
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
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, vault_id, name, login, url, note, encrypted_secret, encrypted_data_key, created_at, updated_at
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


def update_secret(secret_id: int, encrypted_secret: bytes, encrypted_data_key: bytes, login, url, note) -> None:
    conn = get_connection()
    cursor = conn.cursor()

    now = datetime.utcnow().isoformat()

    cursor.execute(
        """
        UPDATE secrets
        SET encrypted_secret = ?,
            encrypted_data_key = ?,
            login = ?,
            url = ?,
            note = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (encrypted_secret, encrypted_data_key, login, url, note, now, secret_id),
    )

    conn.commit()
    conn.close()