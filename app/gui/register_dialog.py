import tkinter as tk
from tkinter import ttk, messagebox

from app.services.user_service import register_user


class RegisterDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Регистрация")
        self.geometry("300x250")

        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username").pack(anchor="w")
        self.username = ttk.Entry(frame)
        self.username.pack(fill="x", pady=5)

        ttk.Label(frame, text="Password").pack(anchor="w")
        self.password = ttk.Entry(frame, show="*")
        self.password.pack(fill="x", pady=5)

        ttk.Label(frame, text="Confirm password").pack(anchor="w")
        self.confirm = ttk.Entry(frame, show="*")
        self.confirm.pack(fill="x", pady=5)

        ttk.Button(frame, text="Зарегистрироваться", command=self.on_register).pack(pady=10)

    def on_register(self, event=None):
        username = self.username.get()
        password = self.password.get()
        confirm = self.confirm.get()

        if not username or not password:
            messagebox.showerror("Ошибка", "Заполни все поля")
            return

        if password != confirm:
            messagebox.showerror("Ошибка", "Пароли не совпадают")
            return

        try:
            register_user(username, password)
            messagebox.showinfo("Успех", "Пользователь создан")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))