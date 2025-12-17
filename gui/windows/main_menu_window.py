# file: gui/windows/main_menu_window.py
import os
import logging
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget, QGridLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QFont

from ..ui.ui_main_menu import Ui_MainMenuWindow
from config import APP_DATA_DIR
from utils.resource_path import resource_path
from utils.scaler import scaler  # <--- [THÊM] Import Scaler

logger = logging.getLogger(__name__)

class MainMenuWindow(QMainWindow):
    def __init__(self, config=None):
        super().__init__()
        self.ui = Ui_MainMenuWindow()
        self.ui.setupUi(self)
        self.config = config if config else {}
        
        self.setup_branding()

        self.practice_button = self.ui.practice_button
        self.competition_button = self.ui.competition_button
        self.stats_button = self.ui.stats_button
        self.exit_button = self.ui.exit_button

    def setup_branding(self):
        branding_config = self.config.get('branding', {})
        
        top_text = branding_config.get('top_text', '')
        footer_text = branding_config.get('footer_text', '')
        left_logo_path = branding_config.get('left_logo_path', '')
        right_logo_path = branding_config.get('right_logo_path', '')
        # Sử dụng Scaler cho kích thước logo nếu cần, ở đây tôi giữ logic config
        logo_w, logo_h = branding_config.get('logo_size', [100, 100])

        original_content = self.ui.centralwidget

        if self.ui.verticalLayout:
            m_left, m_top, m_right, m_bottom = self.ui.verticalLayout.getContentsMargins()
            self.ui.verticalLayout.setContentsMargins(m_left, 5, m_right, m_bottom)

        new_main_widget = QWidget()
        grid_layout = QGridLayout(new_main_widget)
        grid_layout.setContentsMargins(20, 15, 20, 5)

        # Logo Trái
        lbl_left = QLabel()
        if self._load_image_to_label(lbl_left, left_logo_path, logo_w, logo_h):
            grid_layout.addWidget(lbl_left, 0, 0, Qt.AlignTop | Qt.AlignLeft)

        # Logo Phải
        lbl_right = QLabel()
        if self._load_image_to_label(lbl_right, right_logo_path, logo_w, logo_h):
            grid_layout.addWidget(lbl_right, 0, 2, Qt.AlignTop | Qt.AlignRight)

        # Cột Giữa
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # --- Top Text ---
        if top_text:
            # [CẬP NHẬT] Dùng Scaler cho font size
            top_font_size = scaler.scale(24) # Tăng size lên 24 cho hoành tráng
            top_label = QLabel(top_text)
            top_label.setAlignment(Qt.AlignCenter)
            top_label.setStyleSheet(f"""
                color: #f1c40f; 
                font-size: {top_font_size}px; 
                font-weight: bold; 
                text-transform: uppercase;
                margin-bottom: 5px;
                font-family: "Segoe UI", Arial, sans-serif;
            """)
            center_layout.addWidget(top_label)

        # Nội dung gốc
        center_layout.addWidget(original_content, 1)

        # --- Footer ---
        if footer_text:
            footer_font_size = scaler.scale(17)
            footer_label = QLabel(footer_text)
            footer_label.setAlignment(Qt.AlignCenter)
            footer_label.setStyleSheet(f"""
                color: #95a5a6; 
                font-size: {footer_font_size}px; 
                font-style: italic; 
                padding-bottom: 5px;
            """)
            center_layout.addWidget(footer_label)

        grid_layout.addWidget(center_panel, 0, 1)

        grid_layout.setColumnStretch(0, 0)
        grid_layout.setColumnStretch(1, 1)
        grid_layout.setColumnStretch(2, 0)
        grid_layout.setRowStretch(0, 1)

        self.setCentralWidget(new_main_widget)

    def _load_image_to_label(self, label: QLabel, path_str: str, w: int, h: int) -> bool:
        if not path_str: return False
        potential_paths = [os.path.join(APP_DATA_DIR, path_str), path_str, resource_path(f"assets/{path_str}")]
        for p in potential_paths:
            if os.path.exists(p) and os.path.isfile(p):
                pixmap = QPixmap(p)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    label.setPixmap(scaled_pixmap)
                    return True
        return False