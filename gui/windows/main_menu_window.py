# file: gui/windows/main_menu_window.py
import os
import logging
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap, QPainter, QColor
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

        # Biến lưu trữ ảnh nền gốc (đã xử lý mờ) để resize dần
        self.cached_bg_pixmap = None 

        self._apply_labels()
        self._prepare_background_image() # Chuẩn bị ảnh

        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        labels = self.config.get("labels", {})
        self.ui.customer_title_label.setText(labels.get("customer_unit_name", "").upper())
        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "")
        self.ui.title_label.setText(f"{title}\n{subtitle}" if subtitle else title)
        self.ui.footer_label.setText(labels.get("app_footer", ""))

    def _prepare_background_image(self):
        """
        Nạp ảnh 1 lần, làm mờ nó và lưu vào biến cache.
        Việc này giúp resize mượt mà hơn vì không phải làm mờ lại liên tục.
        """
        target_filename = self.config.get("main_logo") or "main_logo.png"
        from config import APP_DATA_DIR
        
        possible_paths = [
            os.path.join(APP_DATA_DIR, "assets", target_filename),
            os.path.join(APP_DATA_DIR, target_filename),
            resource_path(os.path.join("assets", target_filename)),
            resource_path(target_filename)
        ]

        final_path = None
        for p in possible_paths:
            if os.path.exists(p):
                final_path = p
                break
        
        if final_path:
            original_pixmap = QPixmap(final_path)
            if not original_pixmap.isNull():
                # Tạo một bản copy trong suốt
                transparent = QPixmap(original_pixmap.size())
                transparent.fill(Qt.transparent)
                
                painter = QPainter(transparent)
                # Độ mờ 15% (0.15). Chỉnh lên 0.2 hoặc 0.3 nếu muốn rõ hơn.
                painter.setOpacity(0.45) 
                
                # Vẽ ảnh gốc lên nền trong suốt với opacity đã set
                painter.drawPixmap(0, 0, original_pixmap)
                painter.end()
                
                # Lưu vào cache để dùng cho resizeEvent
                self.cached_bg_pixmap = transparent
                logger.info(f"✅ Đã chuẩn bị ảnh nền từ: {final_path}")
                
                # Cập nhật lần đầu
                self._update_background_size()
            else:
                logger.error(f"❌ File ảnh lỗi: {final_path}")
        else:
            logger.warning(f"⚠️ Không tìm thấy '{target_filename}'.")

    def resizeEvent(self, event):
        """Sự kiện khi cửa sổ thay đổi kích thước"""
        self._update_background_size()
        super().resizeEvent(event)

    def _update_background_size(self):
        """Cắt và phóng ảnh để lấp đầy màn hình (Aspect Fill)"""
        if self.cached_bg_pixmap:
            # Lấy kích thước hiện tại của cửa sổ
            window_size = self.ui.watermark_logo.size()
            
            # Scale ảnh theo kiểu: Giữ tỷ lệ, nhưng PHÓNG TO ĐỂ LẤP ĐẦY (Expanding)
            scaled_pixmap = self.cached_bg_pixmap.scaled(
                window_size, 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            
            # Gán vào Label (Label sẽ tự động hiển thị phần trung tâm của ảnh)
            self.ui.watermark_logo.setPixmap(scaled_pixmap)