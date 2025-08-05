# main.py
import sys
import logging
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

def main():
    setup_logging()
    app = QApplication(sys.argv)
    try:
        window = MainWindow()
        window.show()
        exit_code = app.exec()
        sys.exit(exit_code)
    except Exception:
        logging.exception("Ứng dụng bị lỗi không mong đợi")
        sys.exit(1)

if __name__ == "__main__":
    main()
