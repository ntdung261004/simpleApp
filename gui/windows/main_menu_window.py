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
        self.ui = Ui_MainMenu()
        self.ui.setupUi(self)
        self.config = config
        
        labels = self.config.get("labels", {})
        
        # --- MÀU SẮC ---
        gold_color = labels.get("title_color", "#f1c40f")

        # 1. TÊN ĐƠN VỊ
        unit_name = labels.get("customer_unit_name", "TÊN ĐƠN VỊ").upper()
        self.ui.label_unit.setText(unit_name)
        self.ui.label_unit.setStyleSheet(f"color: {gold_color}; background: transparent; letter-spacing: 1px;")
        
        # 2. TIÊU ĐỀ CHÍNH
        title_text = labels.get("app_title", "PHẦN MỀM BẮN SÚNG")
        self.ui.label_title.setText(title_text)
        self.ui.label_title.setStyleSheet("color: white; background: transparent;")
        
        # 3. TIÊU ĐỀ PHỤ
        subtitle_text = labels.get("app_subtitle", "SÚNG TIỂU LIÊN")
        self.ui.label_subtitle.setText(subtitle_text)
        self.ui.label_subtitle.setStyleSheet("color: white; background: transparent;")
        
        # 4. FOOTER
        footer_text = labels.get("app_footer", "Bản quyền © 2025")
        self.ui.label_footer.setText(footer_text)
        
        # 5. LOGO CHÌM
        self.logo_pixmap = None
        logo_name = labels.get("logo_filename", "logo_watermark.png")
        self.logo_opacity = labels.get("logo_opacity", 0.35)
        
        # [THAY ĐỔI] Chỉ tìm file logo do người dùng cấu hình hoặc file mặc định trong assets
        # KHÔNG thêm app_icon.ico vào danh sách này nữa.
        possible_paths = [
            os.path.join(APP_DATA_DIR, logo_name),            # Ưu tiên 1: Thư mục dữ liệu người dùng
            resource_path(os.path.join("assets", logo_name))  # Ưu tiên 2: File assets đi kèm
        ]
        
        for p in possible_paths:
            if os.path.exists(p):
                pix = QPixmap(p)
                if not pix.isNull():
                    self.logo_pixmap = pix
                    break
        
        # Map buttons
        self.practice_button = self.ui.practice_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button

    def paintEvent(self, event):
        """Vẽ logo chìm ở chính giữa màn hình"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Nền tối
        painter.fillRect(self.rect(), QColor("#2c3e50"))
        
        if self.logo_pixmap:
            # [THAY ĐỔI] Giảm xuống 70% chiều cao cửa sổ
            target_h = int(self.height() * 0.70)
            
            if target_h > 0:
                scaled_pixmap = self.logo_pixmap.scaledToHeight(target_h, Qt.SmoothTransformation)
                
                # Center calculation
                x = (self.width() - scaled_pixmap.width()) // 2
                y = (self.height() - scaled_pixmap.height()) // 2
                
                painter.setOpacity(self.logo_opacity)
                painter.drawPixmap(x, y, scaled_pixmap)
            
        painter.setOpacity(1.0)