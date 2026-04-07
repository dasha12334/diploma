from app.config import KEY_SIZE
from app.crypto.aead import encrypt, decrypt
from app.crypto.integrity import make_hmac, verify_hmac
from app.crypto.kdf import derive_key
from app.crypto.random import generate_master_key, generate_salt
from app.crypto.shamir import split_secret, reconstruct_secret
from app.storage.repository import (
    add_audit_event,
    add_share,
    create_vault_meta,
    get_shares,
    get_vault_by_name,
)
from app.utils.serialization import deserialize_share, serialize_share


def create_vault(name: str, password: str, n: int, k: int) -> int:
    """
    Создаёт vault:
    - генерирует мастер-ключ,
    - делит его на доли,
    - сохраняет доли в БД,
    - защищает их ключом, выведенным из пароля.
    """
    if not name:
        raise ValueError("Vault name must not be empty")
    if not password:
        raise ValueError("Password must not be empty")
    if not (2 <= k <= n):
        raise ValueError("Require 2 <= k <= n")

    salt = generate_salt()
    password_key = derive_key(password, salt)

    # Проверка пароля при открытии vault
    verifier = make_hmac(password_key, b"vault-verifier")

    master_key = generate_master_key(KEY_SIZE)
    shares = split_secret(master_key, n=n, k=k)

    vault_id = create_vault_meta(name=name, n=n, k=k, password_salt=salt, password_verifier=verifier)

    for x, y in shares:
        raw_share = serialize_share((x, y))
        encrypted_share = encrypt(raw_share, password_key, associated_data=f"{vault_id}:{x}".encode("utf-8"))
        add_share(vault_id, x, encrypted_share)

    add_audit_event(vault_id, "create_vault", f"Vault '{name}' created with n={n}, k={k}")
    return vault_id


def open_vault(name: str, password: str) -> bytes:
    """
    Открывает vault и восстанавливает мастер-ключ.
    """
    vault = get_vault_by_name(name)
    if not vault:
        raise ValueError("Vault not found")

    salt = vault["password_salt"]
    expected_verifier = vault["password_verifier"]

    password_key = derive_key(password, salt)

    if not verify_hmac(password_key, b"vault-verifier", expected_verifier):
        raise ValueError("Wrong password")

    shares_rows = get_shares(vault["id"])
    if len(shares_rows) < vault["k"]:
        raise ValueError("Not enough shares to reconstruct the secret")

    selected_shares = []
    for row in shares_rows[: vault["k"]]:
        encrypted_share = row["share_payload"]
        x = row["share_index"]

        raw_share = decrypt(
            encrypted_share,
            password_key,
            associated_data=f"{vault['id']}:{x}".encode("utf-8"),
        )
        selected_shares.append(deserialize_share(raw_share))

    master_key = reconstruct_secret(selected_shares, KEY_SIZE)
    add_audit_event(vault["id"], "open_vault", f"Vault '{name}' opened")
    return master_key