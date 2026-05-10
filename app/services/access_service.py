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

def can_assign_role(current_role: str, target_role: str) -> bool:
    """Может ли текущий пользователь назначить целевую роль?"""
    if current_role == ROLE_OWNER:
        return True
    if current_role == ROLE_ADMIN:
        return target_role in (ROLE_USER, ROLE_VIEWER)
    return False

def can_edit_secret(role: str) -> bool:
    """Может ли пользователь редактировать само значение секрета (пароль)?"""
    return role in (ROLE_OWNER, ROLE_ADMIN)

def can_edit_metadata(role: str) -> bool:
    """Может ли пользователь редактировать URL и заметку?"""
    return role in (ROLE_OWNER, ROLE_ADMIN, ROLE_USER)

def can_manage_roles(role: str) -> bool:
    """Может ли пользователь открыть диалог управления ролями?"""
    return role in (ROLE_OWNER, ROLE_ADMIN)