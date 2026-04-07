import tkinter as tk
from tkinter import ttk, messagebox

from app.services.vault_service import create_vault, open_vault
from app.services.secret_service import create_secret, read_secret
from app.storage.repository import get_vault_by_name, get_secrets
from tkinter import filedialog
from app.services.backup_service import export_vault, import_vault

from app.gui.dialogs import CreateVaultDialog, AddSecretDialog
from app.services.secret_service import (
    create_secret,
    read_secret,
    remove_secret,
    edit_secret,
)

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local Vault")
        self.geometry("1000x600")

        # фикс поднятия окна наверх
        self.attributes('-topmost', True)
        self.after(100, lambda: self.attributes('-topmost', False))

        self.current_vault_id = None
        self.current_vault_name = None
        self.current_master_key = None

        self.inactivity_seconds = 0
        self.inactivity_limit = 300  # 5 минут
        self._after_id = None

        self._build_ui()

        self._bind_activity()
        self._start_inactivity_timer()

    def _build_ui(self):
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")

        ttk.Button(top_frame, text="Создать vault", command=self.create_vault_dialog).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Открыть vault", command=self.open_vault_dialog).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Добавить секрет", command=self.add_secret_dialog).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Обновить список", command=self.refresh_secrets).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Показать секрет", command=self.show_selected_secret).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Закрыть vault", command=self.lock_vault).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Редактировать", command=self.edit_secret_dialog).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Удалить", command=self.delete_secret).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Экспорт", command=self.export_vault_dialog).pack(side="left", padx=5)
        ttk.Button(top_frame, text="Импорт", command=self.import_vault_dialog).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Vault не открыт")
        ttk.Label(self, textvariable=self.status_var, padding=10).pack(fill="x")

        table_frame = ttk.Frame(self, padding=10)
        table_frame.pack(fill="both", expand=True)

        columns = ("id", "name", "login", "url", "created_at")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=15)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Название")
        self.tree.heading("login", text="Логин")
        self.tree.heading("url", text="URL")
        self.tree.heading("created_at", text="Создан")

        self.tree.column("id", width=60, anchor="center")
        self.tree.column("name", width=180)
        self.tree.column("login", width=180)
        self.tree.column("url", width=240)
        self.tree.column("created_at", width=180)

        self.tree.pack(fill="both", expand=True)

        self.details = tk.Text(self, height=8)
        self.details.pack(fill="x", padx=10, pady=(0, 10))

    # ======================
    # VAULT
    # ======================

    def create_vault_dialog(self):
        self._reset_inactivity_timer()
        dialog = CreateVaultDialog(self)
        self.wait_window(dialog)

        if not dialog.result:
            return

        name, password, n, k = dialog.result

        try:
            create_vault(name, password, n=n, k=k)
            vault = get_vault_by_name(name)

            self.current_vault_id = vault["id"]
            self.current_vault_name = name
            self.current_master_key = open_vault(name, password)

            self.status_var.set(f"Vault открыт: {name}")
            messagebox.showinfo("Успех", "Vault создан и открыт", parent=self)

            self.refresh_secrets()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def open_vault_dialog(self):
        # пока оставим простой вариант
        self._reset_inactivity_timer()
        from tkinter import simpledialog

        name = simpledialog.askstring("Открыть vault", "Имя vault:", parent=self)
        if not name:
            return

        password = simpledialog.askstring("Открыть vault", "Пароль:", show="*", parent=self)
        if not password:
            return

        try:
            vault = get_vault_by_name(name)
            if not vault:
                raise ValueError("Vault не найден")

            self.current_master_key = open_vault(name, password)
            self.current_vault_id = vault["id"]
            self.current_vault_name = name

            self.status_var.set(f"Vault открыт: {name}")
            messagebox.showinfo("Успех", "Vault открыт", parent=self)

            self.refresh_secrets()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def lock_vault(self):
        self.current_vault_id = None
        self.current_vault_name = None
        self.current_master_key = None
        self.inactivity_seconds = 0

        self.status_var.set("Vault не открыт")
        self.details.delete("1.0", tk.END)

        for item in self.tree.get_children():
            self.tree.delete(item)

    # ======================
    # SECRETS
    # ======================

    def add_secret_dialog(self):
        self._reset_inactivity_timer()
        if self.current_vault_id is None:
            messagebox.showwarning("Внимание", "Сначала открой vault", parent=self)
            return

        dialog = AddSecretDialog(self)
        self.wait_window(dialog)

        if not dialog.result:
            return

        name, login, password, url, note = dialog.result

        try:
            create_secret(
                vault_id=self.current_vault_id,
                master_key=self.current_master_key,
                name=name,
                login=login,
                password=password,
                url=url,
                note=note,
            )

            messagebox.showinfo("Успех", "Секрет добавлен", parent=self)
            self.refresh_secrets()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def refresh_secrets(self):
        self._reset_inactivity_timer()
        for item in self.tree.get_children():
            self.tree.delete(item)

        self.details.delete("1.0", tk.END)

        if self.current_vault_id is None:
            return

        try:
            secrets = get_secrets(self.current_vault_id)

            for row in secrets:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(row["id"]),
                    values=(
                        row["id"],
                        row["name"],
                        row["login"] or "",
                        row["url"] or "",
                        row["created_at"],
                    ),
                )

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def show_selected_secret(self):
        self._reset_inactivity_timer()
        if self.current_master_key is None:
            messagebox.showwarning("Внимание", "Сначала открой vault", parent=self)
            return

        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выбери секрет", parent=self)
            return

        secret_id = int(selected[0])

        try:
            secret = read_secret(secret_id, self.current_master_key)

            text = (
                f"Название: {secret['name']}\n"
                f"Логин: {secret['login']}\n"
                f"Пароль: {secret['password']}\n"
                f"URL: {secret['url']}\n"
                f"Заметка: {secret['note']}\n"
            )

            self.details.delete("1.0", tk.END)
            self.details.insert(tk.END, text)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def delete_secret(self):
        self._reset_inactivity_timer()
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выбери секрет", parent=self)
            return

        secret_id = int(selected[0])

        confirm = messagebox.askyesno("Подтверждение", "Удалить секрет?", parent=self)
        if not confirm:
            return

        try:
            remove_secret(secret_id)
            messagebox.showinfo("Успех", "Секрет удалён", parent=self)
            self.refresh_secrets()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def edit_secret_dialog(self):
        self._reset_inactivity_timer()
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выбери секрет", parent=self)
            return

        if self.current_master_key is None:
            messagebox.showwarning("Внимание", "Сначала открой vault", parent=self)
            return

        secret_id = int(selected[0])

        try:
            secret = read_secret(secret_id, self.current_master_key)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)
            return

        from app.gui.dialogs import AddSecretDialog

        dialog = AddSecretDialog(self)

        # предзаполнение
        dialog.name_entry.insert(0, secret["name"])
        dialog.login_entry.insert(0, secret["login"] or "")
        dialog.password_entry.insert(0, secret["password"])
        dialog.url_entry.insert(0, secret["url"] or "")
        dialog.note_entry.insert(0, secret["note"] or "")

        self.wait_window(dialog)

        if not dialog.result:
            return

        name, login, password, url, note = dialog.result

        try:
            edit_secret(secret_id, self.current_master_key, login, password, url, note)
            messagebox.showinfo("Успех", "Секрет обновлён", parent=self)
            self.refresh_secrets()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def _bind_activity(self):
        events = [
            "<Motion>",
            "<KeyPress>",
            "<Button>",
            "<ButtonRelease>",
        ]

        for event in events:
            self.bind_all(event, self._reset_inactivity_timer, add="+")

    def _reset_inactivity_timer(self, event=None):
        self.inactivity_seconds = 0

    def _start_inactivity_timer(self):
        self.inactivity_seconds += 1

        if self.current_master_key is not None and self.inactivity_seconds >= self.inactivity_limit:
            self.lock_vault()
            messagebox.showwarning(
                "Автоблокировка",
                "Vault заблокирован из-за бездействия.",
                parent=self,
            )
            self.inactivity_seconds = 0
            return

        self._after_id = self.after(1000, self._start_inactivity_timer)

    def export_vault_dialog(self):
        if self.current_vault_id is None or self.current_master_key is None:
            messagebox.showwarning("Внимание", "Сначала открой vault", parent=self)
            return

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Сохранить экспорт",
            defaultextension=".vault",
            filetypes=[("Vault files", "*.vault"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            data = export_vault(self.current_vault_id, self.current_vault_name, self.current_master_key)

            with open(path, "wb") as f:
                f.write(data)

            messagebox.showinfo("Успех", "Vault экспортирован", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def import_vault_dialog(self):
        if self.current_vault_id is None or self.current_master_key is None:
            messagebox.showwarning("Внимание", "Сначала открой vault", parent=self)
            return

        path = filedialog.askopenfilename(
            parent=self,
            title="Открыть экспорт",
            filetypes=[("Vault files", "*.vault"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            with open(path, "rb") as f:
                data = f.read()

            import_vault(self.current_vault_id, self.current_vault_name, self.current_master_key, data)

            messagebox.showinfo("Успех", "Vault импортирован", parent=self)
            self.refresh_secrets()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)