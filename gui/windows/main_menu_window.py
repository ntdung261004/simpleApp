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

        self._apply_labels()
        self._load_watermark_logo()

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

    def _load_watermark_logo(self):
        """
        Tìm và hiển thị main_logo.png từ AppData (ưu tiên) hoặc Resource.
        """
        # Tên file mặc định
        target_filename = "main_logo.png"
        
        # User có thể override tên file trong config nếu muốn
        config_filename = self.config.get("main_logo") or self.config.get("labels", {}).get("main_logo")
        if config_filename:
            target_filename = config_filename

        from config import APP_DATA_DIR
        
        # Logic tìm kiếm file (Ưu tiên AppData để User dễ thay đổi)
        possible_paths = [
            os.path.join(APP_DATA_DIR, "assets", target_filename), # Chuẩn nhất
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
            pixmap = QPixmap(final_path)
            if not pixmap.isNull():
                # Xử lý ảnh: Scale giữ tỷ lệ + Làm mờ
                target_size = self.ui.watermark_logo.size()
                
                scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                
                transparent = QPixmap(scaled.size())
                transparent.fill(Qt.transparent)
                
                painter = QPainter(transparent)
                painter.setOpacity(0.25) # Độ mờ 15%
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                
                self.ui.watermark_logo.setPixmap(transparent)
                logger.info(f"✅ Đã nạp logo nền từ: {final_path}")
            else:
                logger.error(f"❌ File ảnh lỗi: {final_path}")
        else:
            logger.warning(f"⚠️ Không tìm thấy '{target_filename}'. Hãy copy file ảnh vào thư mục assets trong AppData.")