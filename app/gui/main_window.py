import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app.services.vault_service import create_vault, open_vault
from app.storage.repository import get_vault_by_name, get_secrets
from app.services.backup_service import export_vault, import_vault
from app.gui.dialogs import CreateVaultDialog, AddSecretDialog
from app.services.secret_service import (
    create_secret,
    read_secret,
    remove_secret,
    edit_secret,
    search_secrets,
)
from app.gui.access_dialog import AccessDialog


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local Vault")
        self.geometry("1200x650")

        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        self.current_vault_id = None
        self.current_vault_name = None
        self.current_master_key = None
        self.current_user_id = None

        # Для поиска
        self.current_search_term = ""
        self.all_secrets_cache = []  # Кэш всех секретов

        self.inactivity_seconds = 0
        self.inactivity_limit = 300
        self._after_id = None

        self._build_ui()
        self._bind_activity()
        self._start_inactivity_timer()

    # ======================
    # UI
    # ======================

    def _build_ui(self):
        # Главный контейнер
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        # Верхняя панель с кнопками
        top_frame = ttk.Frame(main_container, padding=10)
        top_frame.pack(fill="x")

        # Первая строка кнопок
        button_frame1 = ttk.Frame(top_frame)
        button_frame1.pack(fill="x", pady=2)

        buttons1 = [
            ("Создать vault", self.create_vault_dialog),
            ("Открыть vault", self.open_vault_dialog),
            ("Добавить секрет", self.add_secret_dialog),
            ("Обновить список", self.refresh_secrets),
            ("Показать секрет", self.show_selected_secret),
            ("Закрыть vault", self.lock_vault),
        ]

        for text, command in buttons1:
            ttk.Button(button_frame1, text=text, command=command).pack(side="left", padx=2)

        # Вторая строка кнопок
        button_frame2 = ttk.Frame(top_frame)
        button_frame2.pack(fill="x", pady=2)

        buttons2 = [
            ("Редактировать", self.edit_secret_dialog),
            ("Удалить", self.delete_secret),
            ("Экспорт", self.export_vault_dialog),
            ("Импорт", self.import_vault_dialog),
            ("История версий", self.show_history),
            ("Управление доступом", self.open_access_dialog),
        ]

        for text, command in buttons2:
            ttk.Button(button_frame2, text=text, command=command).pack(side="left", padx=2)

        # Третья строка кнопок (новая)
        button_frame3 = ttk.Frame(top_frame)
        button_frame3.pack(fill="x", pady=2)

        buttons3 = [
            ("🔐 Настройка восстановления", self.setup_recovery),
            ("🔍 Проверить целостность", self.check_integrity),
        ]

        for text, command in buttons3:
            ttk.Button(button_frame3, text=text, command=command).pack(side="left", padx=2)

        # Панель поиска
        search_frame = ttk.LabelFrame(top_frame, text="Поиск и фильтры", padding=5)
        search_frame.pack(fill="x", pady=5)

        # Строка поиска
        entry_frame = ttk.Frame(search_frame)
        entry_frame.pack(fill="x", pady=2)

        ttk.Label(entry_frame, text="🔍", font=("", 12)).pack(side="left", padx=5)

        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)

        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, font=("", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)

        ttk.Button(entry_frame, text="✖ Очистить", width=10, command=self.clear_search).pack(side="right", padx=5)

        # Фильтры
        filter_frame = ttk.Frame(search_frame)
        filter_frame.pack(fill="x", pady=5)

        ttk.Label(filter_frame, text="Фильтровать по:").pack(side="left", padx=5)

        self.filter_var = tk.StringVar(value="all")
        filters = [
            ("Всем полям", "all"),
            ("Логину", "login"),
            ("URL", "url"),
            ("Заметкам", "note"),
        ]

        for text, value in filters:
            ttk.Radiobutton(
                filter_frame,
                text=text,
                value=value,
                variable=self.filter_var,
                command=self.on_search
            ).pack(side="left", padx=10)

        # Статус поиска
        self.search_status_var = tk.StringVar(value="")
        status_label = ttk.Label(
            search_frame,
            textvariable=self.search_status_var,
            foreground="gray",
            font=("", 8)
        )
        status_label.pack(anchor="w", pady=2)

        # Статус vault
        self.status_var = tk.StringVar(value="Vault не открыт")
        ttk.Label(main_container, textvariable=self.status_var, padding=10,
                  font=("", 9, "bold")).pack(fill="x")

        # Таблица секретов
        table_frame = ttk.Frame(main_container, padding=10)
        table_frame.pack(fill="both", expand=True)

        # Контейнер для таблицы со скроллбарами
        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)

        # Настройка колонок
        columns = ("id", "name", "login", "url", "created_at")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings")

        column_configs = {
            "id": {"text": "ID", "width": 50},
            "name": {"text": "Название", "width": 250},
            "login": {"text": "Логин", "width": 180},
            "url": {"text": "URL", "width": 300},
            "created_at": {"text": "Создан", "width": 150},
        }

        for col, config in column_configs.items():
            self.tree.heading(col, text=config["text"])
            self.tree.column(col, width=config["width"], minwidth=50)

        # Вертикальный скроллбар
        v_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=v_scrollbar.set)

        # Горизонтальный скроллбар
        h_scrollbar = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=h_scrollbar.set)

        # Упаковка
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Привязываем обработчик выбора
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.show_selected_secret())

        # Область деталей
        details_frame = ttk.LabelFrame(main_container, text="Детали секрета", padding=10)
        details_frame.pack(fill="x", padx=10, pady=10)

        self.details = tk.Text(details_frame, height=8, wrap="word", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        # Кнопка копирования пароля
        copy_btn = ttk.Button(details_frame, text="📋 Копировать пароль", command=self.copy_password)
        copy_btn.pack(pady=5)

        # Подсказки
        tip_label = ttk.Label(
            main_container,
            text="💡 Подсказка: Двойной клик по секрету показывает детали | Ctrl+F для поиска",
            foreground="gray",
            font=("", 8)
        )
        tip_label.pack(side="bottom", fill="x", padx=10, pady=5)

        # Привязываем горячие клавиши
        self.bind("<Control-f>", lambda e: self.search_entry.focus())
        self.bind("<Control-F>", lambda e: self.search_entry.focus())
        self.bind("<Escape>", lambda e: self.clear_search())

    # ======================
    # ПОИСК
    # ======================

    def on_search(self, *args):
        """Выполняет поиск при вводе текста"""
        search_term = self.search_var.get().strip()
        self.current_search_term = search_term

        if not self.current_vault_id:
            return

        if not search_term or len(search_term) < 2:
            if len(search_term) == 1:
                self.search_status_var.set("Введите минимум 2 символа для поиска")
                return
            self.search_status_var.set("")
            self.refresh_secrets()
            return

        try:
            # Выполняем поиск
            results = search_secrets(self.current_vault_id, self.current_user_id, search_term)

            # Применяем фильтр
            filter_type = self.filter_var.get()
            if filter_type != "all":
                results = [r for r in results if r.get(filter_type)]

            # Очищаем таблицу
            for item in self.tree.get_children():
                self.tree.delete(item)

            # Показываем результаты
            for secret in results:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(secret["id"]),
                    values=(
                        secret["id"],
                        secret["name"],
                        self._highlight_term(secret.get("login", "")[:40]),
                        self._highlight_term(secret.get("url", "")[:50]),
                        secret.get("created_at", "")[:16],
                    ),
                )

            count = len(results)
            self.search_status_var.set(f"🔍 Найдено: {count} секретов по запросу '{search_term}'")

            if count == 0:
                self.details.delete("1.0", tk.END)
                self.details.insert(tk.END, "Ничего не найдено.\nПопробуйте изменить поисковый запрос.")

        except Exception as e:
            self.search_status_var.set(f"Ошибка поиска: {str(e)}")

    def clear_search(self):
        """Очищает поле поиска"""
        self.search_var.set("")
        self.search_entry.focus()
        self.current_search_term = ""
        self.refresh_secrets()

    def _highlight_term(self, text: str) -> str:
        """Подсвечивает найденный термин (маркером)"""
        if not self.current_search_term or len(self.current_search_term) < 2 or not text:
            return text

        term = self.current_search_term.lower()
        text_lower = text.lower()

        if term in text_lower:
            return f"🔍 {text}"
        return text

    def copy_password(self):
        """Копирует пароль из поля деталей в буфер обмена"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Сначала выберите секрет", parent=self)
            return

        # Пароль в тексте после "Пароль: "
        details_text = self.details.get("1.0", tk.END)
        for line in details_text.split('\n'):
            if line.startswith("Пароль:"):
                password = line.replace("Пароль:", "").strip()
                if password:
                    self.clipboard_clear()
                    self.clipboard_append(password)
                    messagebox.showinfo("Скопировано", "Пароль скопирован в буфер обмена", parent=self)
                return

    # ======================
    # VAULT
    # ======================

    def create_vault_dialog(self):
        dialog = CreateVaultDialog(self)
        self.wait_window(dialog)

        if not dialog.result:
            return

        name, password, n, k = dialog.result

        try:
            create_vault(
                name=name,
                password=password,
                n=n,
                k=k,
                owner_id=self.current_user_id
            )

            vault = get_vault_by_name(name)

            self.current_vault_id = vault["id"]
            self.current_vault_name = name
            self.current_master_key = open_vault(name, password)

            self.status_var.set(f"✅ Vault открыт: {name}")
            self.clear_search()
            self.refresh_secrets()

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    # app/gui/main_window.py - измените метод open_vault_dialog:

    def open_vault_dialog(self):
        from tkinter import simpledialog

        # Сначала просим имя vault
        name = simpledialog.askstring("Открыть vault", "Имя vault:", parent=self)
        if not name:
            return

        vault = get_vault_by_name(name)
        if not vault:
            # Если vault не найден, спрашиваем про восстановление
            if messagebox.askyesno("Vault не найден",
                                   f"Vault '{name}' не найден.\n\n"
                                   f"Хотите восстановить доступ из бэкапа?",
                                   parent=self):
                self.open_vault_with_recovery(name)
            return

        # Запрашиваем пароль
        password = simpledialog.askstring("Открыть vault", f"Пароль для vault '{name}':",
                                          show="*", parent=self)

        if not password:
            return

        try:
            self.current_master_key = open_vault(name, password)
            self.current_vault_id = vault["id"]
            self.current_vault_name = name

            self.status_var.set(f"✅ Vault открыт: {name}")
            self.clear_search()
            self.refresh_secrets()

        except Exception as e:
            # Если пароль неверный, предлагаем восстановление
            if "Wrong password" in str(e) or "Too many attempts" in str(e):
                if messagebox.askyesno("Ошибка входа",
                                       f"{str(e)}\n\n"
                                       f"Хотите восстановить доступ к vault '{name}'?\n\n"
                                       f"Потребуется мастер-пароль или бэкап долей.",
                                       parent=self):
                    self.open_vault_with_recovery(name)
            else:
                messagebox.showerror("Ошибка", str(e), parent=self)

    def lock_vault(self):
        self.current_vault_id = None
        self.current_vault_name = None
        self.current_master_key = None

        self.status_var.set("🔒 Vault не открыт")
        self.details.delete("1.0", tk.END)

        for item in self.tree.get_children():
            self.tree.delete(item)

        self.clear_search()

    # ======================
    # SECRETS
    # ======================

    def add_secret_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return

        dialog = AddSecretDialog(self, is_edit=False)
        self.wait_window(dialog)

        if not dialog.result:
            return

        name, login, password, url, note = dialog.result

        try:
            create_secret(
                vault_id=self.current_vault_id,
                master_key=self.current_master_key,
                user_id=self.current_user_id,
                name=name,
                login=login,
                password=password,
                url=url,
                note=note,
            )

            self.refresh_secrets()
            messagebox.showinfo("Успех", "Секрет добавлен", parent=self)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def refresh_secrets(self):
        """Обновляет список секретов (с учётом активного поиска)"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.current_vault_id:
            return

        try:
            # Если есть активный поиск, используем его
            if self.current_search_term and len(self.current_search_term) >= 2:
                self.on_search()
                return

            # Иначе показываем все секреты
            secrets = get_secrets(self.current_vault_id)
            self.search_status_var.set(f"📁 Всего: {len(secrets)} секретов")

            for row in secrets:
                self.tree.insert(
                    "",
                    "end",
                    iid=str(row["id"]),
                    values=(
                        row["id"],
                        row["name"],
                        (row["login"] or "")[:40],
                        (row["url"] or "")[:50],
                        row["created_at"],
                    ),
                )

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def show_selected_secret(self):
        selected = self.tree.selection()
        if not selected:
            return

        secret_id = int(selected[0])

        try:
            secret = read_secret(
                secret_id,
                self.current_master_key,
                self.current_user_id,
            )

            text = f"""
╔══════════════════════════════════════════════════════════╗
║                    ИНФОРМАЦИЯ О СЕКРЕТЕ                  ║
╠══════════════════════════════════════════════════════════╣
║ Название:  {secret['name']}
║ Логин:     {secret.get('login', '—')}
║ Пароль:    {secret.get('password', '—')}
║ URL:       {secret.get('url', '—')}
║ Заметка:   {secret.get('note', '—')}
╠══════════════════════════════════════════════════════════╣
║ Создан:    {secret.get('created_at', '—')}
║ Обновлён:  {secret.get('updated_at', '—')}
║ Версия:    {secret.get('version', 1)}
╚══════════════════════════════════════════════════════════╝
            """

            self.details.delete("1.0", tk.END)
            self.details.insert(tk.END, text)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def delete_secret(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите секрет для удаления", parent=self)
            return

        secret_id = int(selected[0])

        # Подтверждение удаления
        if not messagebox.askyesno("Подтверждение", "Удалить выбранный секрет?", parent=self):
            return

        try:
            remove_secret(
                secret_id,
                self.current_user_id,
                self.current_vault_id,
            )
            self.refresh_secrets()
            self.details.delete("1.0", tk.END)
            messagebox.showinfo("Успех", "Секрет удалён", parent=self)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def edit_secret_dialog(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите секрет для редактирования", parent=self)
            return

        secret_id = int(selected[0])

        try:
            secret = read_secret(
                secret_id,
                self.current_master_key,
                self.current_user_id,
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать секрет: {e}", parent=self)
            return

        dialog = AddSecretDialog(self, is_edit=True)

        dialog.name_entry.insert(0, secret["name"])
        dialog.name_entry.configure(state="disabled")
        dialog.login_entry.insert(0, secret.get("login") or "")
        dialog.password_entry.insert(0, secret.get("password") or "")
        dialog.url_entry.insert(0, secret.get("url") or "")
        dialog.note_entry.insert(0, secret.get("note") or "")

        self.wait_window(dialog)

        if not dialog.result:
            return

        _, login, password, url, note = dialog.result

        if not password:
            messagebox.showerror("Ошибка", "Пароль не может быть пустым", parent=self)
            return

        try:
            edit_secret(
                secret_id,
                self.current_master_key,
                self.current_user_id,
                self.current_vault_id,
                login,
                password,
                url,
                note,
            )

            self.refresh_secrets()
            self.details.delete("1.0", tk.END)
            messagebox.showinfo("Успех", "Секрет обновлён", parent=self)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            with open("edit_error.txt", "w", encoding="utf-8") as f:
                f.write(error_details)
            messagebox.showerror(
                "Ошибка",
                f"Не удалось обновить секрет:\n{str(e)}",
                parent=self
            )

    # ======================
    # EXPORT / IMPORT
    # ======================

    def export_vault_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return

        path = filedialog.asksaveasfilename(defaultextension=".vault")
        if not path:
            return

        data = export_vault(
            self.current_vault_id,
            self.current_vault_name,
            self.current_master_key,
        )

        with open(path, "wb") as f:
            f.write(data)

        messagebox.showinfo("Успех", f"Vault экспортирован в {path}", parent=self)

    def import_vault_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return

        path = filedialog.askopenfilename(filetypes=[("Vault files", "*.vault")])
        if not path:
            return

        with open(path, "rb") as f:
            data = f.read()

        try:
            import_vault(
                self.current_vault_id,
                self.current_vault_name,
                self.current_master_key,
                data,
            )
            self.refresh_secrets()
            messagebox.showinfo("Успех", "Vault импортирован", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    # ======================
    # IDLE
    # ======================

    def _bind_activity(self):
        self.bind_all("<Motion>", self._reset_timer)
        self.bind_all("<Key>", self._reset_timer)

    def _reset_timer(self, event=None):
        self.inactivity_seconds = 0

    def _start_inactivity_timer(self):
        self.inactivity_seconds += 1

        if self.inactivity_seconds >= self.inactivity_limit:
            self.lock_vault()
            messagebox.showwarning("Автоблокировка", "Vault заблокирован из-за бездействия")

            self.inactivity_seconds = 0
            return

        self.after(1000, self._start_inactivity_timer)

    # ======================
    # ДИАЛОГИ
    # ======================

    def open_access_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return
        AccessDialog(self, self.current_vault_id)

    def show_history(self):
        """Показывает историю версий выбранного секрета"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Внимание", "Выберите секрет", parent=self)
            return

        secret_id = int(selected[0])
        secret_name = self.tree.item(selected[0])["values"][1]

        from app.gui.history_dialog import HistoryDialog
        HistoryDialog(
            self,
            secret_id,
            secret_name,
            self.current_master_key,
            self.current_user_id,
            self.current_vault_id
        )

    # app/gui/main_window.py - добавьте эти методы:

    def setup_recovery(self):
        """Настройка восстановления доступа"""
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return

        from app.gui.recovery_dialog import RecoverySetupDialog
        RecoverySetupDialog(
            self,
            self.current_vault_id,
            self.current_vault_name,
            self.current_master_key
        )

    def check_integrity(self):
        """Проверка целостности vault"""
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return

        from app.crypto.integrity import IntegrityChecker
        from app.storage.repository import log_integrity_check

        checker = IntegrityChecker(self.current_master_key)

        try:
            # Показываем прогресс
            progress_dialog = tk.Toplevel(self)
            progress_dialog.title("Проверка целостности")
            progress_dialog.geometry("300x100")
            progress_dialog.transient(self)

            ttk.Label(progress_dialog, text="Проверка целостности данных...").pack(pady=20)
            progress_bar = ttk.Progressbar(progress_dialog, mode="indeterminate")
            progress_bar.pack(pady=10, padx=20, fill="x")
            progress_bar.start()

            self.update()

            # Выполняем проверку
            result = checker.check_vault_integrity(self.current_vault_id)

            progress_bar.stop()
            progress_dialog.destroy()

            # Логируем результат
            log_integrity_check(
                self.current_vault_id,
                result["status"],
                len(result["issues"]),
                str(result)
            )

            # Показываем результат
            self._show_integrity_result(result)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка проверки целостности: {str(e)}", parent=self)

    def _show_integrity_result(self, result: dict):
        """Показывает результат проверки целостности"""
        dialog = tk.Toplevel(self)
        dialog.title("Результат проверки целостности")
        dialog.geometry("600x400")

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill="both", expand=True)

        # Статус
        status_color = "green" if result["status"] == "ok" else "red"
        ttk.Label(frame, text=f"Статус: {result['status'].upper()}",
                  foreground=status_color, font=("", 12, "bold")).pack(anchor="w")

        # Статистика
        stats_frame = ttk.LabelFrame(frame, text="Статистика", padding=10)
        stats_frame.pack(fill="x", pady=10)

        ttk.Label(stats_frame, text=f"Проверено секретов: {result['checked']['secrets']}").pack(anchor="w")
        ttk.Label(stats_frame, text=f"Проверено долей: {result['checked']['shares']}").pack(anchor="w")

        # Проблемы
        if result["issues"]:
            issues_frame = ttk.LabelFrame(frame, text="Обнаружены проблемы", padding=10)
            issues_frame.pack(fill="both", expand=True, pady=10)

            issues_text = tk.Text(issues_frame, height=10, wrap="word")
            issues_text.pack(fill="both", expand=True)

            for issue in result["issues"]:
                if issue["type"] == "secret":
                    issues_text.insert(tk.END, f"❌ Секрет #{issue['id']} '{issue['name']}': {issue['issue']}\n")
                elif issue["type"] == "share":
                    issues_text.insert(tk.END, f"❌ Доля #{issue['index']}: {issue['issue']}\n")
                else:
                    issues_text.insert(tk.END, f"❌ {issue.get('error', 'Неизвестная ошибка')}\n")

            issues_text.configure(state="disabled")
        else:
            ttk.Label(frame, text="✅ Проблем не обнаружено. Все данные в порядке.",
                      foreground="green", font=("", 10)).pack(pady=20)

        ttk.Button(frame, text="Закрыть", command=dialog.destroy).pack(pady=10)

    # app/gui/main_window.py - добавьте этот метод:

    def open_vault_with_recovery(self, vault_name: str):
        """Открывает диалог восстановления при неудачной попытке входа"""
        from app.gui.recovery_dialog import RecoveryDialog
        from app.services.vault_service import recover_vault_from_master_password, recover_vault_from_shares
        from app.storage.repository import get_vault_by_name

        dialog = RecoveryDialog(self, vault_name)
        self.wait_window(dialog)

        if not dialog.result:
            return

        method = dialog.result[0]
        vault = get_vault_by_name(vault_name)

        if not vault:
            messagebox.showerror("Ошибка", f"Vault '{vault_name}' не найден", parent=self)
            return

        try:
            if method == "master":
                _, token, password = dialog.result
                master_key = recover_vault_from_master_password(vault["id"], password, token)

                if master_key:
                    self.current_master_key = master_key
                    self.current_vault_id = vault["id"]
                    self.current_vault_name = vault_name
                    self.status_var.set(f"✅ Vault восстановлен и открыт: {vault_name}")
                    self.refresh_secrets()
                    messagebox.showinfo(
                        "Успех",
                        "Доступ к vault восстановлен!\n"
                        "Теперь вы можете использовать основной пароль для входа.",
                        parent=self
                    )
                else:
                    messagebox.showerror("Ошибка", "Не удалось восстановить доступ", parent=self)

            elif method == "shares":
                _, backup_path = dialog.result
                success = recover_vault_from_shares(vault["id"], backup_path)

                if success:
                    # После восстановления долей, нужно открыть vault с основным паролем
                    messagebox.showinfo(
                        "Успех",
                        "Доли успешно восстановлены!\n"
                        "Теперь вы можете открыть vault с основным паролем.",
                        parent=self
                    )
                    # Предлагаем открыть vault
                    self.open_vault_dialog()
                else:
                    messagebox.showerror("Ошибка", "Не удалось восстановить доли", parent=self)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)