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

        # Cache
        self.cached_bg_pixmap = None 
        self.left_logo_pixmap = None
        self.right_logo_pixmap = None

        self._apply_labels()
        self._prepare_background_image() 
        self._load_side_logos() # Load logo

        # Mapping nút
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.guide_button = self.ui.guide_button
        self.exit_button = self.ui.exit_button
        
    def _apply_labels(self):
        labels = self.config.get("labels", {})
        self.ui.customer_title_label.setText(labels.get("customer_unit_name", "").upper())
        title = labels.get("app_title", "PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM") # Cập nhật default text
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
                painter.setOpacity(0.25) 
                painter.drawPixmap(0, 0, original_pixmap)
                painter.end()
                self.cached_bg_pixmap = transparent
                self._update_background_size()

    def _load_side_logos(self):
        """Load logo trái phải dựa trên tên file trong Config"""
        from config import APP_DATA_DIR
        
        # Lấy tên file từ config (mặc định là .png)
        left_name = self.config.get("left_logo", "left_logo.png")
        right_name = self.config.get("right_logo", "right_logo.png")

        def load_img(filename):
            if not filename: return None
            paths = [
                os.path.join(APP_DATA_DIR, "assets", filename),
                os.path.join(APP_DATA_DIR, filename),
                resource_path(os.path.join("assets", filename)),
                resource_path(filename)
            ]
            for p in paths:
                if os.path.exists(p):
                    pix = QPixmap(p)
                    if not pix.isNull():
                        return pix
            logger.warning(f"⚠️ Không tìm thấy file logo biên: {filename}")
            return None

        self.left_logo_pixmap = load_img(left_name)
        self.right_logo_pixmap = load_img(right_name)
        
        # Ẩn hiện Label
        self.ui.left_logo.setVisible(self.left_logo_pixmap is not None)
        self.ui.right_logo.setVisible(self.right_logo_pixmap is not None)

        self._update_side_logos_size()

    def resizeEvent(self, event):
        self._update_background_size()
        self._update_side_logos_size() 
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

    def _update_side_logos_size(self):
        # Scale logo bằng 25% chiều cao cửa sổ
        target_height = max(100, int(self.height() * 0.25))
        
        if self.left_logo_pixmap:
            scaled = self.left_logo_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            self.ui.left_logo.setPixmap(scaled)
            
        if self.right_logo_pixmap:
            scaled = self.right_logo_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
            self.ui.right_logo.setPixmap(scaled)