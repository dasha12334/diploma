# app/gui/history_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox

from app.services.secret_service import get_secret_history, rollback_secret


class HistoryDialog(tk.Toplevel):
    def __init__(self, parent, secret_id: int, secret_name: str,
                 master_key: bytes, user_id: int, vault_id: int):
        super().__init__(parent)
        self.title(f"История версий: {secret_name}")
        self.geometry("600x400")

        self.secret_id = secret_id
        self.secret_name = secret_name
        self.master_key = master_key
        self.user_id = user_id
        self.vault_id = vault_id
        self.parent = parent

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        # Левый фрейм – таблица со скроллбаром
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True)

        columns = ("version", "url", "created_at")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        self.tree.heading("version", text="Версия")
        self.tree.heading("url", text="URL")
        self.tree.heading("created_at", text="Дата создания")
        self.tree.column("version", width=80)
        self.tree.column("url", width=200)
        self.tree.column("created_at", width=150)

        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Правый фрейм – кнопки вертикально
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="y", padx=(10, 0))

        ttk.Button(right_frame, text="Показать версию", command=self._show_version).pack(fill="x", pady=5)
        ttk.Button(right_frame, text="Откатить к версии", command=self._rollback_version).pack(fill="x", pady=5)
        ttk.Button(right_frame, text="Закрыть", command=self.destroy).pack(fill="x", pady=5)

    def _load_history(self):
        """Загружает историю версий"""
        try:
            versions = get_secret_history(self.secret_id, self.user_id)

            for version in versions:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        version["version"],
                        version["url"][:50] if version["url"] else "",
                        version["created_at"],
                    ),
                    tags=(version["version"],)
                )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить историю: {e}", parent=self)

    def _show_version(self):
        """Показывает выбранную версию"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите версию", parent=self)
            return

        # Получаем номер версии из выбранного элемента
        item = self.tree.item(selection[0])
        version = item["values"][0]

        try:
            from app.services.secret_service import read_secret
            secret = read_secret(
                self.secret_id,
                self.master_key,
                self.user_id,
                version=version
            )

            # Показываем в отдельном окне
            self._show_secret_details(secret, version)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать версию: {e}", parent=self)

    def _rollback_version(self):
        """Откатывает к выбранной версии"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите версию", parent=self)
            return

        item = self.tree.item(selection[0])
        version = item["values"][0]

        # Подтверждение
        if not messagebox.askyesno(
                "Подтверждение",
                f"Откатить секрет '{self.secret_name}' к версии {version}?\n"
                f"Текущая версия будет сохранена как новая.",
                parent=self
        ):
            return

        try:
            rollback_secret(
                self.secret_id,
                version,
                self.master_key,
                self.user_id,
                self.vault_id
            )

            messagebox.showinfo("Успех", f"Секрет откачен к версии {version}", parent=self)
            self.destroy()

            # Обновляем главное окно
            if hasattr(self.parent, 'refresh_secrets'):
                self.parent.refresh_secrets()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось откатить: {e}", parent=self)

    def _show_secret_details(self, secret: dict, version: int):
        """Показывает детали секрета в отдельном окне"""
        dialog = tk.Toplevel(self)
        dialog.title(f"Версия {version}: {secret['name']}")
        dialog.geometry("500x400")

        text = tk.Text(dialog, wrap="word", padx=10, pady=10)
        text.pack(fill="both", expand=True)

        info = f"""
Название: {secret['name']}
Версия: {version}
Пароль: {secret.get('password', '')}
URL: {secret.get('url', '')}
Заметка: {secret.get('note', '')}
Создан: {secret.get('created_at', '')}
Обновлён: {secret.get('updated_at', '')}
        """

        text.insert("1.0", info)
        text.configure(state="disabled")

        # Кнопка копирования пароля
        def copy_password():
            dialog.clipboard_clear()
            dialog.clipboard_append(secret.get('password', ''))
            messagebox.showinfo("Скопировано", "Пароль скопирован в буфер обмена", parent=dialog)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", pady=10)

        ttk.Button(btn_frame, text="Копировать пароль", command=copy_password).pack()