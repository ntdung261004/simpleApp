# file: gui/windows/main_menu_window.py

from PySide6.QtWidgets import QMainWindow
from ..ui.ui_main_menu import Ui_MainMenuWindow

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

        # Cập nhật các chuỗi văn bản từ config
        self._apply_labels()

        # Gán các nút từ giao diện vào thuộc tính của lớp
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        """Lấy các chuỗi văn bản từ config và áp dụng lên giao diện."""
        labels = self.config.get("labels", {})
        
        # Lấy và đặt tiêu đề cho đơn vị khách hàng
        customer_name = labels.get("customer_unit_name", "Tên đơn vị") # Dòng này vẫn đúng
        self.ui.customer_title_label.setText(customer_name.upper())

        # Lấy tiêu đề và phụ đề chính, nếu không có thì dùng giá trị mặc định
        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "SÚNG TIỂU LIÊN")
        
        # Kết hợp và đặt cho label chính
        full_title = f"{title}\n{subtitle}"
        self.ui.title_label.setText(full_title)