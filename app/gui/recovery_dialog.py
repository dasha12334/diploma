# app/gui/recovery_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os

from app.services.recovery_service import RecoveryService
from app.services.backup_shares_service import SharesBackupService


class RecoverySetupDialog(tk.Toplevel):
    def __init__(self, parent, vault_id: int, vault_name: str, master_key: bytes):
        super().__init__(parent)
        self.title(f"Настройка восстановления - {vault_name}")
        self.geometry("500x400")

        self.vault_id = vault_id
        self.vault_name = vault_name
        self.master_key = master_key
        self.parent = parent

        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Вкладка: Мастер-пароль
        master_frame = ttk.Frame(notebook, padding=10)
        notebook.add(master_frame, text="Мастер-пароль")
        self._build_master_tab(master_frame)

        # Вкладка: Бэкап долей
        shares_frame = ttk.Frame(notebook, padding=10)
        notebook.add(shares_frame, text="Бэкап долей")
        self._build_shares_tab(shares_frame)

    def _build_master_tab(self, frame):
        ttk.Label(frame, text="Мастер-пароль для восстановления",
                  font=("", 10, "bold")).pack(anchor="w", pady=5)

        ttk.Label(frame, text="Этот пароль позволит восстановить доступ к vault\n"
                              "даже если вы забыли основной пароль.",
                  foreground="gray").pack(anchor="w", pady=5)

        ttk.Label(frame, text="Мастер-пароль:").pack(anchor="w", pady=(10, 0))
        self.recovery_password = ttk.Entry(frame, show="*")
        self.recovery_password.pack(fill="x", pady=5)

        ttk.Label(frame, text="Подтверждение:").pack(anchor="w")
        self.recovery_password2 = ttk.Entry(frame, show="*")
        self.recovery_password2.pack(fill="x", pady=5)

        ttk.Button(frame, text="Создать мастер-пароль",
                   command=self._setup_master_password).pack(pady=20)

        # Информация
        info_frame = ttk.LabelFrame(frame, text="Важно!", padding=10)
        info_frame.pack(fill="x", pady=10)

        ttk.Label(info_frame, text="• Запишите мастер-пароль в надёжном месте\n"
                                   "• Без мастер-пароля восстановление будет невозможно\n"
                                   "• Храните пароль отдельно от основного",
                  foreground="red").pack(anchor="w")

    def _build_shares_tab(self, frame):
        ttk.Label(frame, text="Резервное копирование долей Шамира",
                  font=("", 10, "bold")).pack(anchor="w", pady=5)

        ttk.Label(frame, text="Доли Шамира - это части мастер-ключа.\n"
                              "Для восстановления потребуется K из N долей.",
                  foreground="gray").pack(anchor="w", pady=5)

        ttk.Label(frame, text="Папка для бэкапа:").pack(anchor="w", pady=(10, 0))

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", pady=5)

        self.backup_path = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.backup_path).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Выбрать", command=self._select_backup_dir).pack(side="right", padx=5)

        ttk.Button(frame, text="Экспортировать доли",
                   command=self._export_shares).pack(pady=20)

        ttk.Label(frame, text="Папка для импорта:").pack(anchor="w", pady=(10, 0))

        import_path_frame = ttk.Frame(frame)
        import_path_frame.pack(fill="x", pady=5)

        self.import_path = tk.StringVar()
        ttk.Entry(import_path_frame, textvariable=self.import_path).pack(side="left", fill="x", expand=True)
        ttk.Button(import_path_frame, text="Выбрать", command=self._select_import_dir).pack(side="right", padx=5)

        ttk.Button(frame, text="Импортировать доли",
                   command=self._import_shares).pack(pady=10)

    def _select_backup_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.backup_path.set(directory)

    def _select_import_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.import_path.set(directory)

    def _setup_master_password(self):
        password = self.recovery_password.get()
        password2 = self.recovery_password2.get()

        if not password:
            messagebox.showerror("Ошибка", "Введите мастер-пароль", parent=self)
            return

        if password != password2:
            messagebox.showerror("Ошибка", "Пароли не совпадают", parent=self)
            return

        try:
            token = RecoveryService.setup_master_password(
                self.vault_id, self.master_key, password
            )

            # Показываем токен
            self._show_recovery_token(token)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def _show_recovery_token(self, token: str):
        """Показывает токен восстановления"""
        dialog = tk.Toplevel(self)
        dialog.title("Код восстановления")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Сохраните этот код в надёжном месте!",
                  font=("", 12, "bold"), foreground="red").pack(pady=10)

        ttk.Label(frame, text="Код восстановления:").pack(anchor="w")

        token_text = tk.Text(frame, height=3, font=("Courier", 10))
        token_text.pack(fill="x", pady=10)
        token_text.insert("1.0", token)
        token_text.configure(state="disabled")

        ttk.Label(frame, text="⚠️ Без этого кода восстановление будет невозможно!",
                  foreground="orange").pack(pady=10)

        def copy_token():
            dialog.clipboard_clear()
            dialog.clipboard_append(token)
            messagebox.showinfo("Скопировано", "Код скопирован в буфер обмена", parent=dialog)

        def save_to_file():
            filepath = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")]
            )
            if filepath:
                with open(filepath, "w") as f:
                    f.write(f"Vault: {self.vault_name}\n")
                    f.write(f"Recovery token: {token}\n")
                    f.write(f"Created: {datetime.now()}\n")
                messagebox.showinfo("Сохранено", f"Код сохранён в {filepath}", parent=dialog)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="Копировать", command=copy_token).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Сохранить в файл", command=save_to_file).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side="right", padx=5)

    def _export_shares(self):
        if not self.backup_path.get():
            messagebox.showerror("Ошибка", "Выберите папку для бэкапа", parent=self)
            return

        try:
            files = SharesBackupService.export_shares(
                self.vault_id, self.backup_path.get()
            )

            messagebox.showinfo(
                "Успех",
                f"Экспортировано {len(files)} долей в папку:\n{self.backup_path.get()}",
                parent=self
            )

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def _import_shares(self):
        if not self.import_path.get():
            messagebox.showerror("Ошибка", "Выберите папку с бэкапами", parent=self)
            return

        # Ищем файлы долей
        share_files = []
        for filename in os.listdir(self.import_path.get()):
            if filename.startswith(f"share_{self.vault_name}_") and filename.endswith(".share"):
                share_files.append(os.path.join(self.import_path.get(), filename))

        if not share_files:
            messagebox.showerror("Ошибка", "Не найдено файлов долей", parent=self)
            return

        # Спрашиваем пароль для расшифровки (если доли зашифрованы)
        password = None
        if messagebox.askyesno("Шифрование", "Доли были зашифрованы паролем?", parent=self):
            from tkinter import simpledialog
            password = simpledialog.askstring("Пароль", "Введите пароль для расшифровки:", show="*")

        try:
            imported = SharesBackupService.import_shares(
                self.vault_id, share_files, password
            )

            messagebox.showinfo(
                "Успех",
                f"Импортировано {imported} долей из {len(share_files)}",
                parent=self
            )

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)


class RecoveryDialog(tk.Toplevel):
    """Диалог восстановления доступа к vault"""

    def __init__(self, parent, vault_name: str):
        super().__init__(parent)
        self.title(f"Восстановление доступа - {vault_name}")
        self.geometry("450x350")

        self.vault_name = vault_name
        self.result = None

        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Восстановление доступа к vault",
                  font=("", 12, "bold")).pack(pady=10)

        ttk.Label(frame, text="Выберите способ восстановления:",
                  foreground="gray").pack(anchor="w", pady=10)

        # Способ 1: Мастер-пароль
        master_frame = ttk.LabelFrame(frame, text="Мастер-пароль", padding=10)
        master_frame.pack(fill="x", pady=5)

        ttk.Label(master_frame, text="Код восстановления:").pack(anchor="w")
        self.recovery_token = ttk.Entry(master_frame)
        self.recovery_token.pack(fill="x", pady=5)

        ttk.Label(master_frame, text="Мастер-пароль:").pack(anchor="w")
        self.recovery_password = ttk.Entry(master_frame, show="*")
        self.recovery_password.pack(fill="x", pady=5)

        ttk.Button(master_frame, text="Восстановить через мастер-пароль",
                   command=self._recover_with_master).pack(pady=10)

        # Способ 2: Бэкап долей
        shares_frame = ttk.LabelFrame(frame, text="Бэкап долей Шамира", padding=10)
        shares_frame.pack(fill="x", pady=5)

        ttk.Label(shares_frame, text="Папка с бэкапами долей:").pack(anchor="w")

        path_frame = ttk.Frame(shares_frame)
        path_frame.pack(fill="x", pady=5)

        self.backup_path = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.backup_path).pack(side="left", fill="x", expand=True)
        ttk.Button(path_frame, text="Выбрать", command=self._select_backup_dir).pack(side="right", padx=5)

        ttk.Button(shares_frame, text="Восстановить из бэкапа долей",
                   command=self._recover_with_shares).pack(pady=10)

        ttk.Button(frame, text="Отмена", command=self.destroy).pack(pady=20)

    def _select_backup_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.backup_path.set(directory)

    def _recover_with_master(self):
        token = self.recovery_token.get()
        password = self.recovery_password.get()

        if not token or not password:
            messagebox.showerror("Ошибка", "Введите код восстановления и мастер-пароль", parent=self)
            return

        self.result = ("master", token, password)
        self.destroy()

    def _recover_with_shares(self):
        if not self.backup_path.get():
            messagebox.showerror("Ошибка", "Выберите папку с бэкапами", parent=self)
            return

        self.result = ("shares", self.backup_path.get())
        self.destroy()