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
        self.geometry("300x270")
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

        ttk.Button(frame, text="Создать", command=self.on_submit).pack(
            fill="x", pady=(10, 0)
        )

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
        self.geometry("500x480")
        self.resizable(False, True)   # разрешить изменение высоты, ширина фиксирована

        self.result = None
        self.is_edit = is_edit
        self.mode_var = tk.IntVar(value=0)

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
            self.name_entry.configure(state="disabled")
            ttk.Label(frame, text="(Название нельзя изменить при редактировании)",
                      foreground="gray").pack(anchor="w")

        # Radiobuttons
        mode_frame = ttk.Frame(frame)
        mode_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(mode_frame, text="Пароль (короткий)", variable=self.mode_var, value=0,
                        command=self._toggle_mode).pack(side="left", padx=5)
        ttk.Radiobutton(mode_frame, text="JSON / длинный текст", variable=self.mode_var, value=1,
                        command=self._toggle_mode).pack(side="left", padx=5)

        # Контейнер для парольного режима
        self.password_frame = ttk.Frame(frame)
        self.password_frame.pack(fill="x", pady=5)
        ttk.Label(self.password_frame, text="Пароль:").pack(anchor="w")
        pass_entry_frame = ttk.Frame(self.password_frame)
        pass_entry_frame.pack(fill="x", pady=2)
        self.password_entry = ttk.Entry(pass_entry_frame, show="*")
        self.password_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(pass_entry_frame, text="🔑 Сгенерировать", command=self.generate_password).pack(side="right", padx=5)

        # Контейнер для большого текста
        self.text_frame = ttk.Frame(frame)
        ttk.Label(self.text_frame, text="Секрет (JSON / текст):").pack(anchor="w")
        # Создаём Text с фиксированной шириной (60 символов) и возможностью растяжения по вертикали
        self.secret_text = tk.Text(self.text_frame, wrap=tk.WORD, font=("TkFixedFont", 10), height=6, width=60)
        self.secret_text.pack(fill="y", expand=True, pady=2)   # только вертикальное расширение

        # URL и Заметка
        ttk.Label(frame, text="URL:").pack(anchor="w")
        self.url_entry = ttk.Entry(frame)
        self.url_entry.pack(fill="x", pady=5)

        ttk.Label(frame, text="Заметка:").pack(anchor="w")
        self.note_entry = ttk.Entry(frame)
        self.note_entry.pack(fill="x", pady=5)

        ttk.Button(frame, text="Сохранить", command=self.on_submit).pack(pady=10)

        self._toggle_mode()   # показать начальный режим

    def _toggle_mode(self):
        if self.mode_var.get() == 0:
            self.password_frame.pack(fill="x", pady=5)
            self.text_frame.pack_forget()
        else:
            # Упаковываем контейнер с растяжением только по вертикали
            self.text_frame.pack(fill="y", expand=True, pady=5)
            self.password_frame.pack_forget()
        self.geometry("")   # сбросить явный размер окна
        self.update_idletasks()

    def generate_password(self):
        """Открывает генератор паролей и вставляет сгенерированный пароль в поле пароля"""
        from app.gui.password_generator import PasswordGeneratorDialog

        def on_password_generated(password):
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, password)

        PasswordGeneratorDialog(self, on_password_generated)

    def on_submit(self):
        try:
            name = self.name_entry.get()
            if self.mode_var.get() == 0:
                secret = self.password_entry.get()
            else:
                secret = self.secret_text.get("1.0", tk.END).strip()
            url = self.url_entry.get()
            note = self.note_entry.get()

            if not secret:
                raise ValueError("Секрет не может быть пустым")
            if not self.is_edit and not name:
                raise ValueError("Название обязательно")

            self.result = (name, secret, url, note)
            self.destroy()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def set_secret(self, value: str):
        """Устанавливает значение секрета в соответствующее поле, определяя режим автоматически"""
        # Если значение содержит перенос строки или длинное (более 50 символов), переключаем в текстовый режим
        if "\n" in value or len(value) > 50:
            self.mode_var.set(1)
            self.secret_text.delete("1.0", tk.END)
            self.secret_text.insert("1.0", value)
        else:
            self.mode_var.set(0)
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, value)
        self._toggle_mode()