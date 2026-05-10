# app/gui/dialogs.py - ИСПРАВЛЕННАЯ ВЕРСИЯ (убрано дублирование)

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
    def __init__(self, parent, is_edit=False):
        super().__init__(parent)
        self.title("Редактировать секрет" if is_edit else "Добавить секрет")
        self.geometry("400x450")
        self.resizable(False, False)

        self.result = None
        self.is_edit = is_edit

        self.transient(parent)
        self.grab_set()

        self._build()

    def _build(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        # Название
        ttk.Label(frame, text="Название:").pack(anchor="w")
        self.name_entry = ttk.Entry(frame)
        self.name_entry.pack(fill="x", pady=5)

        if self.is_edit:
            ttk.Label(frame, text="(Название нельзя изменить при редактировании)",
                      foreground="gray").pack(anchor="w")

        # Пароль (с кнопкой генерации)
        ttk.Label(frame, text="Пароль:").pack(anchor="w")

        pass_frame = ttk.Frame(frame)
        pass_frame.pack(fill="x", pady=5)

        self.password_entry = ttk.Entry(pass_frame, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True)

        ttk.Button(pass_frame, text="🔑 Сгенерировать",
                   command=self.generate_password).pack(side="right", padx=5)

        # URL
        ttk.Label(frame, text="URL:").pack(anchor="w")
        self.url_entry = ttk.Entry(frame)
        self.url_entry.pack(fill="x", pady=5)

        # Заметка
        ttk.Label(frame, text="Заметка:").pack(anchor="w")
        self.note_entry = ttk.Entry(frame)
        self.note_entry.pack(fill="x", pady=5)

        # Кнопка сохранения
        ttk.Button(frame, text="Сохранить", command=self.on_submit).pack(pady=10)

    def on_submit(self):
        try:
            name = self.name_entry.get()
            password = self.password_entry.get()
            url = self.url_entry.get()
            note = self.note_entry.get()

            if not password:
                raise ValueError("Пароль обязателен")

            if not self.is_edit and not name:
                raise ValueError("Название обязательно")

            self.result = (name, password, url, note)
            self.destroy()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def generate_password(self):
        """Открывает генератор паролей"""
        from app.gui.password_generator import PasswordGeneratorDialog

        def on_password_generated(password):
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, password)

        PasswordGeneratorDialog(self, on_password_generated)

    # app/gui/dialogs.py - добавьте в AddSecretDialog метод:

    def _add_context_menu(self, widget):
        """Добавляет контекстное меню для вставки"""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Вставить", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Копировать", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Вырезать", command=lambda: widget.event_generate("<<Cut>>"))

        def show_menu(event):
            menu.post(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_menu)
        widget.bind("<Control-v>", lambda e: widget.event_generate("<<Paste>>"))
        widget.bind("<Control-V>", lambda e: widget.event_generate("<<Paste>>"))