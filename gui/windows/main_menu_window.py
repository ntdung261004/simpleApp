# file: gui/windows/main_menu_window.py
import os
import logging
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap
from ..ui.ui_main_menu import Ui_MainMenuWindow
from utils.resource_path import resource_path # Hàm quan trọng để xử lý đường dẫn

# Cấu hình logger (nếu chưa có)
logger = logging.getLogger(__name__)

class MainMenuWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)

        self._apply_labels()
        self._load_logos() # <-- Gọi hàm nạp logo mới

        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        labels = self.config.get("labels", {})
        
        customer_name = labels.get("customer_unit_name", "")
        self.ui.customer_title_label.setText(customer_name)

        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "")
        full_title = f"{title}\n{subtitle}" if subtitle else title
        self.ui.title_label.setText(full_title)

        footer_text = labels.get("app_footer", "")
        self.ui.footer_label.setText(footer_text)

    def _load_logos(self):
        """
        Phiên bản sửa lỗi: Tự động tìm key trong cả root và labels, 
        và tự động dò tìm file trong thư mục assets.
        """
        # --- SỬA ĐỔI: Tìm ở root trước, nếu không có thì tìm trong labels ---
        labels_config = self.config.get("labels", {})
        
        left_path_raw = self.config.get("logo_left") or labels_config.get("logo_left")
        right_path_raw = self.config.get("logo_right") or labels_config.get("logo_right")
        # -------------------------------------------------------------------

        # Import APP_DATA_DIR tại chỗ
        from config import APP_DATA_DIR

        def smart_find_and_set(path_raw, label_widget, position_name):
            if not path_raw:
                # Nếu vẫn không thấy, lúc này mới coi là chưa cấu hình
                return 

            # Danh sách các đường dẫn "nghi ngờ" có thể chứa ảnh
            possible_paths = []

            # 1. Đường dẫn tuyệt đối từ Config
            possible_paths.append(path_raw)

            # 2. Nằm trong AppData/assets (trường hợp config chỉ ghi tên file 'logo.png')
            # Logic: Nếu chưa có chữ 'assets' trong đường dẫn, thử chèn vào
            if "assets" not in path_raw:
                possible_paths.append(os.path.join(APP_DATA_DIR, "assets", path_raw))
            else:
                possible_paths.append(os.path.join(APP_DATA_DIR, path_raw))

            # 3. Nằm trong source code gốc (dùng resource_path)
            possible_paths.append(resource_path(path_raw))
            if "assets" not in path_raw:
                possible_paths.append(resource_path(os.path.join("assets", path_raw)))

            # Bắt đầu đi tìm...
            final_path = None
            for p in possible_paths:
                norm_p = os.path.normpath(p)
                if os.path.exists(norm_p):
                    final_path = norm_p
                    break
            
            # Kết quả
            if final_path:
                pixmap = QPixmap(final_path)
                if not pixmap.isNull():
                    label_widget.setPixmap(pixmap)
                    logger.info(f"✅ Đã hiện logo {position_name} từ: {final_path}")
                else:
                    logger.error(f"❌ File tồn tại nhưng lỗi định dạng ảnh: {final_path}")
            else:
                logger.warning(f"⚠️ Không tìm thấy logo {position_name}. Đã thử tìm tại: {possible_paths}")

        # Thực thi
        smart_find_and_set(left_path_raw, self.ui.logo_left, "LEFT")
        smart_find_and_set(right_path_raw, self.ui.logo_right, "RIGHT")