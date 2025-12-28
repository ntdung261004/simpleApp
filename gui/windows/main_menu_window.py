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

        # Cache ảnh nền
        self.cached_bg_pixmap = None 

        self._apply_labels()
        self._prepare_background_image() 

        # --- MAPPING NÚT ---
        # Ánh xạ các nút từ UI sang thuộc tính của class
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.guide_button = self.ui.guide_button  # MỚI: Thêm dòng này
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        labels = self.config.get("labels", {})
        self.ui.customer_title_label.setText(labels.get("customer_unit_name", "").upper())
        title = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        subtitle = labels.get("app_subtitle", "")
        self.ui.title_label.setText(f"{title}\n{subtitle}" if subtitle else title)
        self.ui.footer_label.setText(labels.get("app_footer", ""))

    def _prepare_background_image(self):
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
                transparent = QPixmap(original_pixmap.size())
                transparent.fill(Qt.transparent)
                painter = QPainter(transparent)
                painter.setOpacity(0.45) 
                painter.drawPixmap(0, 0, original_pixmap)
                painter.end()
                self.cached_bg_pixmap = transparent
                self._update_background_size()
            else:
                logger.error(f"❌ File ảnh lỗi: {final_path}")
        else:
            logger.warning(f"⚠️ Không tìm thấy '{target_filename}'.")

    def resizeEvent(self, event):
        self._update_background_size()
        super().resizeEvent(event)

    def _update_background_size(self):
        if self.cached_bg_pixmap:
            window_size = self.ui.watermark_logo.size()
            scaled_pixmap = self.cached_bg_pixmap.scaled(
                window_size, 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            )
            self.ui.watermark_logo.setPixmap(scaled_pixmap)