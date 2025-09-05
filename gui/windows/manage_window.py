# file: gui/manage_window.py
from PySide6.QtWidgets import QMainWindow
from ..ui.ui_manage import ManageGui

class ManageWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = ManageGui()
        self.setCentralWidget(self.ui)

        # Các hàm xử lý dữ liệu và sự kiện sẽ được thêm vào đây