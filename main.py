from app.storage.db import init_db
from app.gui import MainWindow


def main():
    init_db()
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()


