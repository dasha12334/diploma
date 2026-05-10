# app/gui/login_dialog.py - ИСПРАВЛЕННАЯ ВЕРСИЯ (без восстановления)

import tkinter as tk
from tkinter import ttk, messagebox

from app.services.auth_service import authenticate
from app.gui.register_dialog import RegisterDialog


class LoginDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Вход в систему")
        self.geometry("300x220")
        self.resizable(False, False)

        self.user = None

        self._build()

        # Центрируем
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Имя пользователя:").pack(anchor="w")
        self.username = ttk.Entry(frame)
        self.username.pack(fill="x", pady=5)

        ttk.Label(frame, text="Пароль:").pack(anchor="w")
        self.password = ttk.Entry(frame, show="*")
        self.password.pack(fill="x", pady=5)

        ttk.Button(frame, text="Войти", command=self._login).pack(pady=5)
        ttk.Button(frame, text="Регистрация", command=self._open_register).pack()

        # Привязываем Enter
        self.password.bind("<Return>", lambda e: self._login())
        self.username.bind("<Return>", lambda e: self.password.focus())

    def _login(self):
        user = authenticate(
            self.username.get(),
            self.password.get(),
        )

        if not user:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            return

        self.user = user
        self.destroy()

    def _open_register(self):
        RegisterDialog(self)