from app.storage.repository import get_user_role
from app.constants import ROLE_OWNER, ROLE_ADMIN, ROLE_USER, ROLE_VIEWER


def check_access(user_id: int, vault_id: int, action: str) -> bool:
    role = get_user_role(user_id, vault_id)

    if role == ROLE_OWNER:
        return True

    if role == ROLE_ADMIN:
        return action in ["read", "create", "update"]

    if role == ROLE_USER:
        return action == "read"

    if role == ROLE_VIEWER:
        return action == "read"

    return False