# file: main.py
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

# Nhớ đổi tên file và di chuyển file theo cấu trúc mới
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")

        # QStackedWidget để quản lý các màn hình
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Khởi tạo các màn hình (windows)
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow()

        # Thêm các màn hình vào StackedWidget
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)

        # Kết nối tín hiệu từ các nút bấm của Main Menu
        self.connect_signals()

        # Hiển thị màn hình Main Menu đầu tiên
        self.show_main_menu()

    def connect_signals(self):
        # Khi nút "TẬP LUYỆN" được nhấn, gọi hàm show_practice_screen
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        
        # Khi nút "THOÁT" được nhấn, gọi hàm self.close (hàm có sẵn của QMainWindow)
        self.main_menu.exit_button.clicked.connect(self.close)
        
        # Khi nút "Quay Lại" trên màn hình practice được nhấn, quay về menu chính
        self.practice_screen.gui.backButton.clicked.connect(self.show_main_menu)
        # TODO: Kết nối các nút khác ở đây khi bạn tạo các màn hình tương ứng
        # self.main_menu.stats_button.clicked.connect(self.show_stats_screen)

        # Khi cửa sổ tập luyện muốn quay về menu (cần thêm nút back trong practice_window)
        # self.practice_screen.back_button.clicked.connect(self.show_main_menu)

    def show_main_menu(self):
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self):
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        # Bắt đầu camera khi chuyển đến màn hình tập luyện
        self.practice_screen.start_camera()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    controller = ApplicationController()
    controller.showFullScreen()
    sys.exit(app.exec())