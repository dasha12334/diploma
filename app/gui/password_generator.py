# app/gui/password_generator.py

import tkinter as tk
from tkinter import ttk, messagebox
import secrets
import string


class PasswordGeneratorDialog(tk.Toplevel):
    def __init__(self, parent, on_password_selected):
        super().__init__(parent)
        self.title("Генератор паролей")
        self.geometry("500x400")

        self.on_password_selected = on_password_selected
        self.current_password = ""

        self._build_ui()
        self._generate()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=10)
        frame.pack(fill="both", expand=True)

        # Параметры генерации
        params_frame = ttk.LabelFrame(frame, text="Параметры", padding=10)
        params_frame.pack(fill="x", pady=5)

        # Длина пароля
        ttk.Label(params_frame, text="Длина:").grid(row=0, column=0, sticky="w", padx=5)
        self.length_var = tk.IntVar(value=16)
        length_spin = ttk.Spinbox(params_frame, from_=8, to=64, textvariable=self.length_var, width=10)
        length_spin.grid(row=0, column=1, sticky="w", padx=5)
        length_spin.bind("<KeyRelease>", lambda e: self._generate())

        # Чекбоксы для символов
        self.use_upper = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame, text="Заглавные буквы (A-Z)",
                        variable=self.use_upper, command=self._generate).grid(row=1, column=0, columnspan=2, sticky="w",
                                                                              padx=5)

        self.use_lower = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame, text="Строчные буквы (a-z)",
                        variable=self.use_lower, command=self._generate).grid(row=2, column=0, columnspan=2, sticky="w",
                                                                              padx=5)

        self.use_digits = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame, text="Цифры (0-9)",
                        variable=self.use_digits, command=self._generate).grid(row=3, column=0, columnspan=2,
                                                                               sticky="w", padx=5)

        self.use_symbols = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame, text="Спецсимволы (!@#$%^&*)",
                        variable=self.use_symbols, command=self._generate).grid(row=4, column=0, columnspan=2,
                                                                                sticky="w", padx=5)

        # Сгенерированный пароль
        pass_frame = ttk.LabelFrame(frame, text="Сгенерированный пароль", padding=10)
        pass_frame.pack(fill="x", pady=10)

        self.password_var = tk.StringVar()
        password_entry = ttk.Entry(pass_frame, textvariable=self.password_var,
                                   font=("Courier", 12), state="readonly")
        password_entry.pack(fill="x", padx=5, pady=5)

        # Кнопки
        btn_frame = ttk.Frame(pass_frame)
        btn_frame.pack(fill="x", pady=5)

        ttk.Button(btn_frame, text="Сгенерировать ещё", command=self._generate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Копировать", command=self._copy_password).pack(side="left", padx=5)

        # Кнопка использования
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x", pady=10)

        ttk.Button(button_frame, text="Использовать этот пароль",
                   command=self._use_password).pack(fill="x", padx=5)
        ttk.Button(button_frame, text="Отмена",
                   command=self.destroy).pack(fill="x", padx=5, pady=5)

    def _generate(self, event=None):
        """Генерирует новый пароль"""
        length = self.length_var.get()

        chars = ""
        if self.use_upper.get():
            chars += string.ascii_uppercase
        if self.use_lower.get():
            chars += string.ascii_lowercase
        if self.use_digits.get():
            chars += string.digits
        if self.use_symbols.get():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

        if not chars:
            messagebox.showwarning("Внимание", "Выберите хотя бы один тип символов", parent=self)
            return

        # Генерируем криптографически стойкий пароль
        password = ''.join(secrets.choice(chars) for _ in range(length))
        self.current_password = password
        self.password_var.set(password)

    def _copy_password(self):
        """Копирует пароль в буфер обмена"""
        self.clipboard_clear()
        self.clipboard_append(self.current_password)
        messagebox.showinfo("Скопировано", "Пароль скопирован в буфер обмена", parent=self)

    def _use_password(self):
        """Использует сгенерированный пароль"""
        if self.on_password_selected:
            self.on_password_selected(self.current_password)
        self.destroy()