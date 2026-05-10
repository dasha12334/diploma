# app/gui/search_dialog.py

import tkinter as tk
from tkinter import ttk, messagebox

from app.services.secret_service import search_secrets


class SearchDialog(tk.Toplevel):
    def __init__(self, parent, vault_id: int, user_id: int, master_key: bytes, on_select_callback):
        super().__init__(parent)
        self.title("Поиск секретов")
        self.geometry("700x500")

        self.vault_id = vault_id
        self.user_id = user_id
        self.master_key = master_key
        self.on_select = on_select_callback

        self._build_ui()

    def _build_ui(self):
        # Верхняя панель поиска
        top_frame = ttk.Frame(self, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Поиск:").pack(side="left", padx=5)
        self.search_entry = ttk.Entry(top_frame, width=40)
        self.search_entry.pack(side="left", padx=5, fill="x", expand=True)

        ttk.Button(top_frame, text="Найти", command=self._search).pack(side="left", padx=5)

        # Привязываем Enter для поиска
        self.search_entry.bind("<Return>", lambda e: self._search())

        # Результаты
        result_frame = ttk.Frame(self, padding=10)
        result_frame.pack(fill="both", expand=True)

        # Таблица результатов
        columns = ("id", "name", "login", "url", "updated_at")
        self.tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=20)

        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Название")
        self.tree.heading("login", text="Логин")
        self.tree.heading("url", text="URL")
        self.tree.heading("updated_at", text="Обновлён")

        self.tree.column("id", width=50)
        self.tree.column("name", width=200)
        self.tree.column("login", width=150)
        self.tree.column("url", width=200)
        self.tree.column("updated_at", width=150)

        # Скроллбар
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Двойной клик для выбора
        self.tree.bind("<Double-Button-1>", self._on_select)

        # Кнопки внизу
        button_frame = ttk.Frame(self, padding=10)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Выбрать", command=self._on_select).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Закрыть", command=self.destroy).pack(side="right", padx=5)

        # Статус
        self.status_var = tk.StringVar(value="Введите поисковый запрос")
        ttk.Label(self, textvariable=self.status_var, padding=10).pack(fill="x")

    def _search(self):
        """Выполняет поиск"""
        search_term = self.search_entry.get().strip()

        if len(search_term) < 2:
            messagebox.showwarning("Внимание", "Введите минимум 2 символа для поиска", parent=self)
            return

        # Очищаем результаты
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.status_var.set("Поиск...")
            self.update()

            results = search_secrets(self.vault_id, self.user_id, search_term)

            if not results:
                self.status_var.set(f"Ничего не найдено по запросу: '{search_term}'")
                return

            for secret in results:
                self.tree.insert(
                    "",
                    "end",
                    values=(
                        secret["id"],
                        secret["name"],
                        secret["login"][:30] if secret["login"] else "",
                        secret["url"][:40] if secret["url"] else "",
                        secret["updated_at"][:16] if secret["updated_at"] else "",
                    ),
                    tags=(secret["id"],)
                )

            self.status_var.set(f"Найдено {len(results)} секретов")

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)
            self.status_var.set("Ошибка поиска")

    def _on_select(self, event=None):
        """Выбирает секрет и закрывает окно"""
        selected = self.tree.selection()
        if not selected:
            return

        item = self.tree.item(selected[0])
        secret_id = item["values"][0]

        self.destroy()
        if self.on_select:
            self.on_select(secret_id)