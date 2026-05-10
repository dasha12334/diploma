import tkinter as tk
from tkinter import ttk, messagebox

from app.storage.repository import get_all_users, grant_user_access
from app.constants import ROLE_OWNER, ROLE_ADMIN, ROLE_USER, ROLE_VIEWER
from app.services.access_service import can_assign_role


class AccessDialog(tk.Toplevel):
    def __init__(self, parent, vault_id: int, current_role: str, current_user_id: int):
        super().__init__(parent)
        self.title("Управление доступом")
        self.geometry("400x300")
        self.vault_id = vault_id
        self.parent = parent
        self.current_role = current_role
        self.current_user_id = current_user_id
        self.users = get_all_users()
        self._build_ui()
        self._load_users()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Пользователь:").pack(anchor="w")
        self.user_combo = ttk.Combobox(frame, state="readonly")
        self.user_combo.pack(fill="x")

        ttk.Label(frame, text="Роль:").pack(anchor="w", pady=(10, 0))

        if self.current_role == ROLE_OWNER:
            allowed_roles = ["viewer", "user", "admin", "owner"]
        elif self.current_role == ROLE_ADMIN:
            allowed_roles = ["viewer", "user"]
        else:
            allowed_roles = []

        if allowed_roles:
            self.role_combo = ttk.Combobox(frame, state="readonly", values=allowed_roles)
            self.role_combo.pack(fill="x")
            self.btn_assign = ttk.Button(frame, text="Назначить роль", command=self._assign_role)
            self.btn_assign.pack(pady=15)
        else:
            ttk.Label(frame, text="У вас нет прав на назначение ролей", foreground="red").pack(pady=10)
            self.role_combo = None
            self.btn_assign = None

    def _load_users(self):
        self.user_map = {}
        user_names = []
        for user in self.users:
            # Если текущий пользователь – владелец, исключаем его из списка (нельзя менять свою роль)
            if self.current_role == ROLE_OWNER and user["id"] == self.current_user_id:
                continue
            display = f"{user['username']} (id={user['id']})"
            user_names.append(display)
            self.user_map[display] = user["id"]
        self.user_combo["values"] = user_names

    def _assign_role(self):
        if not self.role_combo:
            return
        user_display = self.user_combo.get()
        role = self.role_combo.get()
        if not user_display or not role:
            messagebox.showerror("Ошибка", "Выберите пользователя и роль", parent=self)
            return
        if not can_assign_role(self.current_role, role):
            messagebox.showerror("Ошибка", "У вас нет прав на назначение этой роли", parent=self)
            return
        user_id = self.user_map[user_display]
        try:
            grant_user_access(user_id, self.vault_id, role)
            messagebox.showinfo("Готово", f"Роль '{role}' назначена пользователю {user_display}", parent=self)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)