# file: gui/windows/main_menu_window.py
import os
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPixmap, QColor
from PySide6.QtCore import Qt
from gui.ui.ui_main_menu import Ui_MainMenu
from utils.resource_path import resource_path
from config import APP_DATA_DIR

class MainMenuWindow(QWidget):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ui = Ui_MainMenu()
        self.ui.setupUi(self) # Giao diện đã được scale sẵn trong setupUi
        
        # --- 1. Load Text từ Config ---
        labels = self.config.get("labels", {})
        
        # Tên đơn vị (Màu lấy từ config nếu có, không thì theo CSS mặc định)
        unit_name = labels.get("customer_unit_name", "TÊN ĐƠN VỊ")
        self.ui.label_unit.setText(unit_name)
        
        # Cập nhật màu vàng từ config (ghi đè CSS nếu cần)
        gold_color = labels.get("title_color", "#f1c40f")
        current_style = self.ui.label_unit.styleSheet()
        # Chèn thêm màu vào style hiện tại
        self.ui.label_unit.setStyleSheet(current_style + f"color: {gold_color};")

        # Tiêu đề
        self.ui.label_title.setText(labels.get("app_title", "PHẦN MỀM BẮN SÚNG"))
        self.ui.label_subtitle.setText(labels.get("app_subtitle", "SÚNG TIỂU LIÊN"))
        self.ui.label_footer.setText(labels.get("app_footer", "Bản quyền © 2025"))
        
        # --- 2. Load Logo Watermark ---
        self.logo_pixmap = None
        logo_name = labels.get("logo_filename", "logo_watermark.png")
        self.logo_opacity = labels.get("logo_opacity", 0.35)
        
        possible_paths = [
            os.path.join(APP_DATA_DIR, logo_name),
            resource_path(os.path.join("assets", logo_name))
        ]
        
        for p in possible_paths:
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    self.logo_pixmap = pix
                    break
        
        # --- 3. Map Buttons ---
        # Ánh xạ để main.py có thể gọi
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button

    def paintEvent(self, event):
        """Vẽ Logo Watermark (Giữ nguyên logic vẽ nền)"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Vẽ nền tối
        painter.fillRect(self.rect(), QColor("#2c3e50"))
        
        if self.logo_pixmap:
            # Logo chiếm 70% chiều cao cửa sổ
            target_h = int(self.height() * 0.70)
            
            if target_h > 0:
                scaled_pixmap = self.logo_pixmap.scaledToHeight(target_h, Qt.SmoothTransformation)
                
                # Căn giữa màn hình
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2
                
                painter.setOpacity(self.logo_opacity)
                painter.drawPixmap(x, y, scaled_pixmap)
            
        painter.setOpacity(1.0)