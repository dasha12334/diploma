from app.storage.db import init_db
from app.gui.main_window import MainWindow
from app.gui.login_dialog import LoginDialog


def main():
    # 🔥 1. Инициализация БД
    init_db()
    print("DB initialized")  # чтобы убедиться, что реально вызывается

    # 🔥 2. Создаём главное окно (пока скрыто)
    app = MainWindow()
    app.withdraw()

    # 🔥 3. Показываем логин
    login_dialog = LoginDialog(app)
    app.wait_window(login_dialog)

    # ❌ если пользователь закрыл окно
    if not login_dialog.user:
        app.destroy()
        return

    # ✅ успешный логин
    user = login_dialog.user

    # 🔥 4. сохраняем пользователя
    app.current_user_id = user["id"]
    app.current_username = user["username"]

    print(f"Logged in as: {user['username']}")

    # 🔥 5. показываем основное окно
    app.deiconify()

    # 🔥 6. запуск
    app.mainloop()


if __name__ == "__main__":
    main()