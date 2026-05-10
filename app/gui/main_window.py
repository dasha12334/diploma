# app/gui/main_window.py – НОВАЯ ВЕРСИЯ С ПЕРЕРАБОТАННЫМ UI

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


class SecretDetailsDialog(tk.Toplevel):
    """Окно для отображения деталей секрета (всплывающее)"""
    def __init__(self, parent, secret: dict):
        super().__init__(parent)
        self.title(f"Детали секрета: {secret['name']}")
        self.geometry("500x450")
        self.resizable(False, False)
        self.secret = secret

        frame = ttk.Frame(self, padding=15)
        frame.pack(fill="both", expand=True)

        # Заполнение информацией
        info_text = f"""
╔══════════════════════════════════════════════════════════╗
║                    ИНФОРМАЦИЯ О СЕКРЕТЕ                  ║
╠══════════════════════════════════════════════════════════╣
║ Название:  {secret['name']}
║ Секрет:    {secret.get('password', '—')}
║ URL:       {secret.get('url', '—')}
║ Заметка:   {secret.get('note', '—')}
╠══════════════════════════════════════════════════════════╣
║ Создан:    {secret.get('created_at', '—')}
║ Обновлён:  {secret.get('updated_at', '—')}
║ Версия:    {secret.get('version', 1)}
╚══════════════════════════════════════════════════════════╝
        """
        text_widget = tk.Text(frame, wrap="word", font=("Consolas", 10))
        text_widget.pack(fill="both", expand=True)
        text_widget.insert("1.0", info_text)
        text_widget.configure(state="disabled")

        # Кнопка копирования пароля
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="📋 Копировать пароль",
                   command=self._copy_password).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Закрыть", command=self.destroy).pack(side="right", padx=5)

        # Центрирование
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

    def _copy_password(self):
        self.clipboard_clear()
        self.clipboard_append(self.secret.get('password', ''))
        messagebox.showinfo("Скопировано", "Пароль скопирован в буфер обмена", parent=self)


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Local Vault")
        self.geometry("1300x700")

        self.attributes("-topmost", True)
        self.after(100, lambda: self.attributes("-topmost", False))

        self.current_vault_id = None
        self.current_vault_name = None
        self.current_master_key = None
        self.current_user_id = None

        # Для поиска
        self.current_search_term = ""

        self.inactivity_seconds = 0
        self.inactivity_limit = 300

        self._build_ui()
        self._bind_activity()
        self._start_inactivity_timer()

    # ======================
    # UI
    # ======================
    def _build_ui(self):
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        # ---------- Верхняя панель (управление vault) ----------
        top_frame = ttk.LabelFrame(main_container, text="Управление хранилищем", padding=5)
        top_frame.pack(fill="x", padx=10, pady=5)

        vault_buttons = [
            ("➕ Создать vault", self.create_vault_dialog),
            ("🔓 Открыть vault", self.open_vault_dialog),
            ("🔒 Закрыть vault", self.lock_vault),
            ("📤 Экспорт", self.export_vault_dialog),
            ("📥 Импорт", self.import_vault_dialog),
            ("👥 Управление доступом", self.open_access_dialog),
            ("🔐 Настройка восстановления", self.setup_recovery),
            ("🔍 Проверить целостность", self.check_integrity),
        ]
        for text, cmd in vault_buttons:
            ttk.Button(top_frame, text=text, command=cmd).pack(side="left", padx=4, pady=2)

        # ---------- Панель поиска ----------
        search_frame = ttk.LabelFrame(main_container, text="Поиск и фильтры", padding=5)
        search_frame.pack(fill="x", padx=10, pady=5)

        entry_frame = ttk.Frame(search_frame)
        entry_frame.pack(fill="x", pady=2)
        ttk.Label(entry_frame, text="🔍", font=("", 12)).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.on_search)
        self.search_entry = ttk.Entry(entry_frame, textvariable=self.search_var, font=("", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(entry_frame, text="✖ Очистить", width=10, command=self.clear_search).pack(side="right", padx=5)

        filter_frame = ttk.Frame(search_frame)
        filter_frame.pack(fill="x", pady=5)
        ttk.Label(filter_frame, text="Фильтровать по:").pack(side="left", padx=5)
        self.filter_var = tk.StringVar(value="all")
        for text, val in [("Всем полям", "all"), ("URL", "url"), ("Заметкам", "note")]:
            ttk.Radiobutton(filter_frame, text=text, value=val, variable=self.filter_var,
                            command=self.on_search).pack(side="left", padx=10)
        self.search_status_var = tk.StringVar()
        ttk.Label(search_frame, textvariable=self.search_status_var, foreground="gray", font=("", 8)).pack(anchor="w", pady=2)

        # ---------- Панель управления секретами ----------
        secrets_panel = ttk.Frame(main_container)
        secrets_panel.pack(fill="x", padx=10, pady=5)
        ttk.Button(secrets_panel, text="➕ Добавить секрет", command=self.add_secret_dialog).pack(side="left", padx=4)
        ttk.Button(secrets_panel, text="🔄 Обновить список", command=self.refresh_secrets).pack(side="left", padx=4)

        # ---------- Таблица секретов + панель действий ----------
        table_and_actions = ttk.Frame(main_container)
        table_and_actions.pack(fill="both", expand=True, padx=10, pady=5)

        # Левая часть: таблица
        table_frame = ttk.Frame(table_and_actions)
        table_frame.pack(side="left", fill="both", expand=True)

        tree_container = ttk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True)

        # Колонки: без "actions"
        columns = ("name", "url", "created_at")
        self.tree = ttk.Treeview(tree_container, columns=columns, show="headings")
        self.tree.heading("name", text="Название")
        self.tree.heading("url", text="URL")
        self.tree.heading("created_at", text="Создан")
        self.tree.column("name", width=250)
        self.tree.column("url", width=300)
        self.tree.column("created_at", width=150)

        v_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree.yview)
        h_scroll = ttk.Scrollbar(tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")
        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Правая панель с кнопками
        actions_frame = ttk.LabelFrame(table_and_actions, text="Действия над секретом", padding=10)
        actions_frame.pack(side="right", fill="y", padx=(10, 0), pady=0)

        # Кнопки (изначально disabled)
        self.btn_show = ttk.Button(actions_frame, text="👁 Показать", command=self.show_selected_secret,
                                   state="disabled")
        self.btn_edit = ttk.Button(actions_frame, text="✏️ Редактировать", command=self.edit_secret_dialog,
                                   state="disabled")
        self.btn_delete = ttk.Button(actions_frame, text="🗑️ Удалить", command=self.delete_secret, state="disabled")
        self.btn_history = ttk.Button(actions_frame, text="📜 История версий", command=self.show_history,
                                      state="disabled")

        self.btn_show.pack(fill="x", pady=5)
        self.btn_edit.pack(fill="x", pady=5)
        self.btn_delete.pack(fill="x", pady=5)
        self.btn_history.pack(fill="x", pady=5)

        # Привязываем событие выбора строки
        self.tree.bind("<<TreeviewSelect>>", self._on_secret_selected)

        self.tree.bind("<Button-3>", self._show_context_menu)
        # Двойной клик → показать секрет
        self.tree.bind("<Double-1>", lambda e: self.show_selected_secret())

        # Статус
        self.status_var = tk.StringVar(value="Vault не открыт")
        ttk.Label(main_container, textvariable=self.status_var, padding=10, font=("", 9, "bold")).pack(fill="x")

        # Подсказка
        ttk.Label(main_container, text="💡 Ctrl+F – поиск | Двойной клик – показать секрет",
                  foreground="gray", font=("", 8)).pack(side="bottom", fill="x", padx=10, pady=5)

        self.bind("<Control-f>", lambda e: self.search_entry.focus())
        self.bind("<Control-F>", lambda e: self.search_entry.focus())
        self.bind("<Escape>", lambda e: self.clear_search())

    # ======================
    # ПОИСК
    # ======================
    def on_search(self, *args):
        term = self.search_var.get().strip()
        self.current_search_term = term
        if not self.current_vault_id:
            return
        if not term or len(term) < 2:
            self.search_status_var.set("")
            self.refresh_secrets()
            return
        try:
            results = search_secrets(self.current_vault_id, self.current_user_id, term)
            filter_type = self.filter_var.get()
            if filter_type != "all":
                results = [r for r in results if r.get(filter_type)]
            for item in self.tree.get_children():
                self.tree.delete(item)
            for sec in results:
                # Внутри on_search, при вставке результатов:
                self.tree.insert("", "end", iid=str(sec["id"]),
                                 values=(sec["name"],
                                         sec.get("url", "")[:50],
                                         sec.get("created_at", "")[:16]))
                # (без последнего элемента)
            self.search_status_var.set(f"🔍 Найдено: {len(results)}")
        except Exception as e:
            self.search_status_var.set(f"Ошибка: {e}")

    def clear_search(self):
        self.search_var.set("")
        self.search_entry.focus()
        self.current_search_term = ""
        self.refresh_secrets()

    # ======================
    # VAULT
    # ======================
    def create_vault_dialog(self):
        dialog = CreateVaultDialog(self)
        self.wait_window(dialog)
        if not dialog.result:
            return
        name, pwd, n, k = dialog.result
        try:
            create_vault(name, pwd, n, k, self.current_user_id)
            vault = get_vault_by_name(name)
            self.current_vault_id = vault["id"]
            self.current_vault_name = name
            self.current_master_key = open_vault(name, pwd)
            self.status_var.set(f"✅ Vault открыт: {name}")
            self.clear_search()
            self.refresh_secrets()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def open_vault_dialog(self):
        from tkinter import simpledialog
        name = simpledialog.askstring("Открыть vault", "Имя vault:", parent=self)
        if not name:
            return
        vault = get_vault_by_name(name)
        if not vault:
            if messagebox.askyesno("Vault не найден", f"Vault '{name}' не найден.\nХотите восстановить доступ из бэкапа?", parent=self):
                self.open_vault_with_recovery(name)
            return
        pwd = simpledialog.askstring("Открыть vault", f"Пароль для vault '{name}':", show="*", parent=self)
        if not pwd:
            return
        try:
            self.current_master_key = open_vault(name, pwd)
            self.current_vault_id = vault["id"]
            self.current_vault_name = name
            self.status_var.set(f"✅ Vault открыт: {name}")
            self.clear_search()
            self.refresh_secrets()
        except Exception as e:
            if "Wrong password" in str(e) or "Too many attempts" in str(e):
                if messagebox.askyesno("Ошибка входа", f"{str(e)}\n\nХотите восстановить доступ?", parent=self):
                    self.open_vault_with_recovery(name)
            else:
                messagebox.showerror("Ошибка", str(e), parent=self)

    def lock_vault(self):
        self.current_vault_id = None
        self.current_master_key = None
        self.current_vault_name = None
        self.status_var.set("🔒 Vault не открыт")
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
        dlg = AddSecretDialog(self, is_edit=False)
        self.wait_window(dlg)
        if not dlg.result:
            return
        name, pwd, url, note = dlg.result
        try:
            create_secret(self.current_vault_id, self.current_master_key, self.current_user_id,
                          name, pwd, url, note)
            self.refresh_secrets()
            messagebox.showinfo("Успех", "Секрет добавлен", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def show_selected_secret(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Инфо", "Выберите секрет", parent=self)
            return
        secret_id = int(sel[0])
        try:
            secret = read_secret(secret_id, self.current_master_key, self.current_user_id)
            SecretDetailsDialog(self, secret)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def delete_secret(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите секрет для удаления", parent=self)
            return
        secret_id = int(sel[0])
        if not messagebox.askyesno("Подтверждение", "Удалить выбранный секрет?", parent=self):
            return
        try:
            remove_secret(secret_id, self.current_user_id, self.current_vault_id)
            self.refresh_secrets()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def refresh_secrets(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        if not self.current_vault_id:
            return
        try:
            secrets = get_secrets(self.current_vault_id)
            for row in secrets:
                self.tree.insert("", "end", iid=str(row["id"]), values=(
                    row["name"],
                    (row["url"] or "")[:50],
                    row["created_at"]
                ))
            # После обновления снимаем выделение → кнопки отключатся
            self._on_secret_selected()
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    def edit_secret_dialog(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите секрет для редактирования", parent=self)
            return
        secret_id = int(sel[0])
        try:
            secret = read_secret(secret_id, self.current_master_key, self.current_user_id)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать секрет: {e}", parent=self)
            return
        dlg = AddSecretDialog(self, is_edit=True)
        dlg.name_entry.insert(0, secret["name"])
        dlg.name_entry.configure(state="disabled")
        dlg.password_entry.insert(0, secret.get("password") or "")
        dlg.url_entry.insert(0, secret.get("url") or "")
        dlg.note_entry.insert(0, secret.get("note") or "")
        self.wait_window(dlg)
        if not dlg.result:
            return
        _, pwd, url, note = dlg.result
        if not pwd:
            messagebox.showerror("Ошибка", "Пароль не может быть пустым", parent=self)
            return
        try:
            edit_secret(secret_id, self.current_master_key, self.current_user_id, self.current_vault_id,
                        pwd, url, note)
            self.refresh_secrets()
            messagebox.showinfo("Успех", "Секрет обновлён", parent=self)
        except Exception as e:
            import traceback
            with open("edit_error.txt", "w") as f:
                f.write(traceback.format_exc())
            messagebox.showerror("Ошибка", str(e), parent=self)

    # ======================
    # EXPORT/IMPORT
    # ======================
    def export_vault_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return
        path = filedialog.asksaveasfilename(defaultextension=".vault")
        if not path:
            return
        data = export_vault(self.current_vault_id, self.current_vault_name, self.current_master_key)
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
            import_vault(self.current_vault_id, self.current_vault_name, self.current_master_key, data)
            self.refresh_secrets()
            messagebox.showinfo("Успех", "Vault импортирован", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    # ======================
    # ДРУГИЕ ДИАЛОГИ
    # ======================
    def open_access_dialog(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return
        AccessDialog(self, self.current_vault_id)

    def show_history(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Внимание", "Выберите секрет", parent=self)
            return
        secret_id = int(sel[0])
        secret_name = self.tree.item(sel[0])["values"][0]
        from app.gui.history_dialog import HistoryDialog
        HistoryDialog(self, secret_id, secret_name, self.current_master_key, self.current_user_id, self.current_vault_id)

    def setup_recovery(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return
        from app.gui.recovery_dialog import RecoverySetupDialog
        RecoverySetupDialog(self, self.current_vault_id, self.current_vault_name, self.current_master_key)

    def check_integrity(self):
        if not self.current_vault_id:
            messagebox.showwarning("Внимание", "Сначала откройте vault", parent=self)
            return
        from app.crypto.integrity import IntegrityChecker
        from app.storage.repository import log_integrity_check
        checker = IntegrityChecker(self.current_master_key)
        try:
            progress = tk.Toplevel(self)
            progress.title("Проверка")
            progress.geometry("300x100")
            ttk.Label(progress, text="Проверка целостности...").pack(pady=20)
            pb = ttk.Progressbar(progress, mode="indeterminate")
            pb.pack(pady=10, padx=20, fill="x")
            pb.start()
            self.update()
            result = checker.check_vault_integrity(self.current_vault_id)
            pb.stop()
            progress.destroy()
            log_integrity_check(self.current_vault_id, result["status"], len(result["issues"]), str(result))
            self._show_integrity_result(result)
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка проверки: {e}", parent=self)

    def _show_integrity_result(self, result):
        dlg = tk.Toplevel(self)
        dlg.title("Результат проверки целостности")
        dlg.geometry("600x400")
        frame = ttk.Frame(dlg, padding=10)
        frame.pack(fill="both", expand=True)
        color = "green" if result["status"] == "ok" else "red"
        ttk.Label(frame, text=f"Статус: {result['status'].upper()}", foreground=color, font=("", 12, "bold")).pack(anchor="w")
        stats = ttk.LabelFrame(frame, text="Статистика", padding=10)
        stats.pack(fill="x", pady=10)
        ttk.Label(stats, text=f"Проверено секретов: {result['checked']['secrets']}").pack(anchor="w")
        ttk.Label(stats, text=f"Проверено долей: {result['checked']['shares']}").pack(anchor="w")
        if result["issues"]:
            issues = ttk.LabelFrame(frame, text="Проблемы", padding=10)
            issues.pack(fill="both", expand=True)
            txt = tk.Text(issues, height=10, wrap="word")
            txt.pack(fill="both", expand=True)
            for iss in result["issues"]:
                if iss["type"] == "secret":
                    txt.insert(tk.END, f"❌ Секрет #{iss['id']} '{iss['name']}': {iss['issue']}\n")
                elif iss["type"] == "share":
                    txt.insert(tk.END, f"❌ Доля #{iss['index']}: {iss['issue']}\n")
                else:
                    txt.insert(tk.END, f"❌ {iss.get('error', 'Ошибка')}\n")
            txt.configure(state="disabled")
        else:
            ttk.Label(frame, text="✅ Проблем не обнаружено", foreground="green", font=("", 10)).pack(pady=20)
        ttk.Button(frame, text="Закрыть", command=dlg.destroy).pack(pady=10)

    # ======================
    # ВОССТАНОВЛЕНИЕ
    # ======================
    def open_vault_with_recovery(self, vault_name: str):
        from app.gui.recovery_dialog import RecoveryDialog
        from app.services.vault_service import recover_vault_from_master_password, recover_vault_from_shares
        dlg = RecoveryDialog(self, vault_name)
        self.wait_window(dlg)
        if not dlg.result:
            return
        method = dlg.result[0]
        vault = get_vault_by_name(vault_name)
        if not vault:
            messagebox.showerror("Ошибка", f"Vault '{vault_name}' не найден", parent=self)
            return
        try:
            if method == "master":
                _, token, pwd = dlg.result
                master_key = recover_vault_from_master_password(vault["id"], pwd, token)
                if master_key:
                    self.current_master_key = master_key
                    self.current_vault_id = vault["id"]
                    self.current_vault_name = vault_name
                    self.status_var.set(f"✅ Vault восстановлен и открыт: {vault_name}")
                    self.refresh_secrets()
                    messagebox.showinfo("Успех", "Доступ восстановлен. Теперь вы можете использовать основной пароль.", parent=self)
                else:
                    messagebox.showerror("Ошибка", "Не удалось восстановить доступ", parent=self)
            elif method == "shares":
                _, backup_path = dlg.result
                success = recover_vault_from_shares(vault["id"], backup_path)
                if success:
                    messagebox.showinfo("Успех", "Доли восстановлены. Теперь откройте vault основным паролем.", parent=self)
                    self.open_vault_dialog()
                else:
                    messagebox.showerror("Ошибка", "Не удалось восстановить доли", parent=self)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e), parent=self)

    # ======================
    # INACTIVITY
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

    def _show_context_menu(self, event):
        """Показывает контекстное меню для выбранного секрета"""
        # Выделяем строку, на которой кликнули
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="👁 Показать секрет", command=self.show_selected_secret)
        menu.add_command(label="✏️ Редактировать", command=self.edit_secret_dialog)
        menu.add_command(label="🗑️ Удалить", command=self.delete_secret)
        menu.add_command(label="📜 История версий", command=self.show_history)
        menu.post(event.x_root, event.y_root)

    def _on_secret_selected(self, event=None):
        """Активирует кнопки действий, если выбран секрет"""
        selected = self.tree.selection()
        state = "normal" if selected else "disabled"
        self.btn_show.config(state=state)
        self.btn_edit.config(state=state)
        self.btn_delete.config(state=state)
        self.btn_history.config(state=state)