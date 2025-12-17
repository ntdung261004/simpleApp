# file: gui/windows/main_menu_window.py
import os
import logging
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from ..ui.ui_main_menu import Ui_MainMenuWindow
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class MainMenuWindow(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)

        self._apply_labels()
        self._load_logos()

        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        labels = self.config.get("labels", {})
        
        customer_name = labels.get("customer_unit_name", "")
        self.ui.customer_title_label.setText(customer_name.upper())

        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "")
        full_title = f"{title}\n{subtitle}" if subtitle else title
        self.ui.title_label.setText(full_title)

        footer_text = labels.get("app_footer", "")
        self.ui.footer_label.setText(footer_text)

    def _load_logos(self):
        """
        Nạp logo, tự động tìm kiếm đường dẫn và scale ảnh giữ tỷ lệ.
        """
        labels_config = self.config.get("labels", {})
        
        left_path_raw = self.config.get("logo_left") or labels_config.get("logo_left")
        right_path_raw = self.config.get("logo_right") or labels_config.get("logo_right")

        from config import APP_DATA_DIR

        def smart_find_and_set(path_raw, label_widget, position_name):
            if not path_raw:
                return 

            possible_paths = []
            possible_paths.append(path_raw)
            if "assets" not in path_raw:
                possible_paths.append(os.path.join(APP_DATA_DIR, "assets", path_raw))
            else:
                possible_paths.append(os.path.join(APP_DATA_DIR, path_raw))
            possible_paths.append(resource_path(path_raw))
            if "assets" not in path_raw:
                possible_paths.append(resource_path(os.path.join("assets", path_raw)))

            final_path = None
            for p in possible_paths:
                norm_p = os.path.normpath(p)
                if os.path.exists(norm_p):
                    final_path = norm_p
                    break
            
            if final_path:
                pixmap = QPixmap(final_path)
                if not pixmap.isNull():
                    # --- XỬ LÝ SCALE ẢNH GIỮ TỶ LỆ ---
                    # Lấy kích thước khung chứa (đã được scale theo màn hình trong UI)
                    target_size = label_widget.size() 
                    
                    # Scale pixmap theo kích thước khung, giữ tỷ lệ, và làm mượt ảnh
                    scaled_pixmap = pixmap.scaled(
                        target_size, 
                        Qt.KeepAspectRatio, 
                        Qt.SmoothTransformation
                    )
                    
                    label_widget.setPixmap(scaled_pixmap)
                    logger.info(f"✅ Đã hiện logo {position_name} từ: {final_path}")
                else:
                    logger.error(f"❌ File tồn tại nhưng lỗi định dạng ảnh: {final_path}")
            else:
                logger.warning(f"⚠️ Không tìm thấy logo {position_name}.")

        smart_find_and_set(left_path_raw, self.ui.logo_left, "LEFT")
        smart_find_and_set(right_path_raw, self.ui.logo_right, "RIGHT")