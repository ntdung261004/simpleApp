# file: gui/windows/main_menu_window.py

from PySide6.QtWidgets import QMainWindow
from ..ui.ui_main_menu import Ui_MainMenuWindow

class MainMenuWindow(QMainWindow):
    """
    Lớp điều khiển logic cho cửa sổ Menu chính.
    
    Lớp này kế thừa QMainWindow để hoạt động như một cửa sổ độc lập và
    sử dụng lớp Ui_MainMenuWindow (từ file ui_main_menu.py) để thiết lập 
    giao diện người dùng.
    """
    def __init__(self):
        """
        Hàm khởi tạo của cửa sổ Menu chính.
        """
        super().__init__()

        # Khởi tạo giao diện người dùng từ lớp Ui_MainMenuWindow
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)
        
        # Gán các nút từ giao diện vào thuộc tính của lớp để dễ truy cập hơn
        # Điều này giúp cho file main.py có thể truy cập trực tiếp các nút này
        # ví dụ: self.main_menu.practice_button.clicked.connect(...)
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.list_button = self.ui.list_button
        self.guide_button = self.ui.guide_button
        self.exit_button = self.ui.exit_button
        # Tại đây, chúng ta không kết nối trực tiếp các sự kiện (ví dụ: self.practice_button.clicked.connect(...))
        # Thay vào đó, việc kết nối sẽ được thực hiện ở lớp ApplicationController trong main.py
        # để giữ cho logic chuyển đổi màn hình được quản lý tập trung ở một nơi.