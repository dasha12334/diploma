import tkinter as tk
from tkinter import ttk, messagebox


class CreateVaultDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Создать vault")
        self.geometry("300x250")
        self.resizable(False, False)

        self.result = None

        self.transient(parent)
        self.grab_set()

        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Имя vault:").pack(anchor="w")
        self.name_entry = ttk.Entry(frame)
        self.name_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="Пароль:").pack(anchor="w")
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="n:").pack(anchor="w")
        self.n_entry = ttk.Entry(frame)
        self.n_entry.insert(0, "5")
        self.n_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="k:").pack(anchor="w")
        self.k_entry = ttk.Entry(frame)
        self.k_entry.insert(0, "3")
        self.k_entry.pack(fill="x", pady=5)

        ttk.Button(frame, text="Создать", command=self.on_submit).pack(pady=10)

    def on_submit(self):
        try:
            name = self.name_entry.get()
            password = self.password_entry.get()
            n = int(self.n_entry.get())
            k = int(self.k_entry.get())

            if not name or not password:
                raise ValueError("Заполни все поля")

            self.result = (name, password, n, k)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)


class AddSecretDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Добавить секрет")
        self.geometry("350x350")
        self.resizable(False, False)

        self.result = None

        self.transient(parent)
        self.grab_set()

        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Название:").pack(anchor="w")
        self.name_entry = ttk.Entry(frame)
        self.name_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="Логин:").pack(anchor="w")
        self.login_entry = ttk.Entry(frame)
        self.login_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="Пароль:").pack(anchor="w")
        self.password_entry = ttk.Entry(frame, show="*")
        self.password_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="URL:").pack(anchor="w")
        self.url_entry = ttk.Entry(frame)
        self.url_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="Заметка:").pack(anchor="w")
        self.note_entry = ttk.Entry(frame)
        self.note_entry.pack(fill="x", pady=5)

        ttk.Button(frame, text="Сохранить", command=self.on_submit).pack(pady=10)

    def on_submit(self):
        try:
            name = self.name_entry.get()
            login = self.login_entry.get()
            password = self.password_entry.get()
            url = self.url_entry.get()
            note = self.note_entry.get()

            if not name or not password:
                raise ValueError("Название и пароль обязательны")

            self.result = (name, login, password, url, note)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)