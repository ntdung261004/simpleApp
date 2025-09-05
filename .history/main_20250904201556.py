# file: main.py
import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] (%(name)s) - %(message)s',
    stream=sys.stdout,
)

from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm")
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow()
        
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        
        self.connect_signals()
        self.show_main_menu()

    def connect_signals(self):
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        self.main_menu.exit_button.clicked.connect(self.close)
        
        if hasattr(self.practice_screen.gui, 'back_button'):
             self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)

    def show_main_menu(self):
        if self.stacked_widget.currentWidget() == self.practice_screen:
            self.practice_screen.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self):
        logging.info("MAIN: Yêu cầu chuyển sang màn hình luyện tập.")
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        # Sửa tên hàm cho đúng với logic mới
        self.practice_screen.start_practice()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    controller = ApplicationController()
    controller.showFullScreen()
    sys.exit(app.exec())