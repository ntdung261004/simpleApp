# file: gui/windows/main_menu_window.py
import os
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap
from ..ui.ui_main_menu import Ui_MainMenuWindow
from utils.resource_path import resource_path

class MainMenuWindow(QMainWindow):
    """
    Lớp điều khiển logic cho cửa sổ Menu chính.
    """
    def __init__(self, config: dict):
        """
        Hàm khởi tạo của cửa sổ Menu chính.
        
        Args:
            config (dict): Đối tượng chứa cấu hình được tải từ config.json.
        """
        super().__init__()

        self.config = config
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)

        # Tải và hiển thị logo
        self._load_logos()

        # Cập nhật các chuỗi văn bản từ config
        self._apply_labels()

        # Gán các nút từ giao diện vào thuộc tính của lớp
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button

    def _load_logos(self):
        """
        Tìm, tải và hiển thị các file logo lên giao diện.
        """
        # Đường dẫn tới các file logo (bạn cần tự tạo)
        logo_left_path = resource_path(os.path.join("assets", "images", "logo_left.png"))
        logo_right_path = resource_path(os.path.join("assets", "images", "logo_right.png"))

        # Tải và đặt logo bên trái
        if os.path.exists(logo_left_path):
            self.ui.logo_left_label.setPixmap(QPixmap(logo_left_path))
        else:
            print(f"Lỗi: Không tìm thấy file logo bên trái tại: {logo_left_path}")

        # Tải và đặt logo bên phải
        if os.path.exists(logo_right_path):
            self.ui.logo_right_label.setPixmap(QPixmap(logo_right_path))
        else:
            print(f"Lỗi: Không tìm thấy file logo bên phải tại: {logo_right_path}")
        
    def _apply_labels(self):
        """Lấy các chuỗi văn bản từ config và áp dụng lên giao diện."""
        labels = self.config.get("labels", {})
        
        customer_name = labels.get("customer_unit_name", "")
        self.ui.customer_title_label.setText(customer_name.upper())

        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "SÚNG TIỂU LIÊN")
        full_title = f"{title}\n{subtitle}"
        self.ui.title_label.setText(full_title)

        # Lấy và hiển thị dòng thông tin ở footer
        footer_text = labels.get("app_footer", "LTSoftware - v1.0.2") # Giá trị mặc định
        self.ui.footer_label.setText(footer_text)