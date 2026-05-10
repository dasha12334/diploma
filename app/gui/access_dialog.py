# app/gui/access_dialog.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import tkinter as tk
from tkinter import ttk, messagebox

from app.storage.repository import get_all_users, get_user_role, grant_user_access


class AccessDialog(tk.Toplevel):
    def __init__(self, parent, vault_id: int):
        super().__init__(parent)
        self.title("Управление доступом")
        self.geometry("400x300")

        self.vault_id = vault_id
        self.parent = parent

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

        self.role_combo = ttk.Combobox(
            frame,
            state="readonly",
            values=["viewer", "user", "admin", "owner"],
        )
        self.role_combo.pack(fill="x")

        ttk.Button(
            frame,
            text="Назначить роль",
            command=self._assign_role,
        ).pack(pady=15)

    def _load_users(self):
        self.user_map = {}

        user_names = []
        for user in self.users:
            display = f"{user['username']} (id={user['id']})"
            user_names.append(display)
            self.user_map[display] = user["id"]

        self.user_combo["values"] = user_names

    def _assign_role(self):
        user_display = self.user_combo.get()
        role = self.role_combo.get()

        if not user_display or not role:
            messagebox.showerror("Ошибка", "Выбери пользователя и роль", parent=self)
            return

        user_id = self.user_map[user_display]

        try:
            grant_user_access(user_id, self.vault_id, role)

            messagebox.showinfo(
                "Готово",
                f"Роль '{role}' назначена пользователю {user_display}",
                parent=self
            )

            self.destroy()  # Закрываем диалог после успешного назначения

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)