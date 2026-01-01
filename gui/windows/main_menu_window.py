# file: gui/windows/main_menu_window.py
import os
import logging
from PySide6.QtWidgets import QMainWindow
from PySide6.QtGui import QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Qt
from ..ui.ui_main_menu import Ui_MainMenuWindow
from utils.resource_path import resource_path
from utils.password_manager import get_info
from gui.windows.password_dialog import PasswordManagerDialog, PasswordEntryDialog
from PySide6.QtWidgets import QMenu, QMessageBox

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
        # Gán các thuộc tính nút để tương thích với phần controller
        self._attach_buttons()

        # Add "Cài đặt mật khẩu" menu in the window menu bar
        try:
            menu_bar = self.menuBar()
            settings_menu = menu_bar.addMenu("Cài đặt")
            pwd_action = QAction("Quản lý mật khẩu", self)
            pwd_action.triggered.connect(lambda: PasswordManagerDialog.open(self))
            settings_menu.addAction(pwd_action)
        except Exception:
            # Không bắt buộc tồn tại menu bar trong một số môi trường
            pass

    def _apply_labels(self):
        """Áp nhãn từ config vào UI"""
        labels = self.config.get("labels", {})
        try:
            self.ui.customer_title_label.setText(labels.get("customer_unit_name", "").upper())
            title = labels.get("app_title", "PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM")
            subtitle = labels.get("app_subtitle", "")
            self.ui.title_label.setText(f"{title}\n{subtitle}" if subtitle else title)
            self.ui.footer_label.setText(labels.get("app_footer", ""))
        except Exception:
            logger.exception("Lỗi khi áp nhãn cho MainMenuWindow")

    def _prepare_background_image(self):
        """Load and cache a translucent watermark background image if available."""
        target_filename = self.config.get("main_logo") or "main_logo.png"
        try:
            from config import APP_DATA_DIR
            possible_paths = [
                os.path.join(APP_DATA_DIR, "assets", target_filename),
                os.path.join(APP_DATA_DIR, target_filename),
                resource_path(os.path.join("assets", target_filename)),
                resource_path(target_filename)
            ]
            final_path = next((p for p in possible_paths if p and os.path.exists(p)), None)
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
        except Exception:
            logger.exception("Lỗi khi chuẩn bị ảnh nền")

    def _load_side_logos(self):
        """Load left and right logos based on config and update labels visibility/size."""
        try:
            from config import APP_DATA_DIR
            left_name = self.config.get("left_logo", "left_logo.png")
            right_name = self.config.get("right_logo", "right_logo.png")

            def load_img(filename):
                if not filename:
                    return None
                paths = [
                    os.path.join(APP_DATA_DIR, "assets", filename),
                    os.path.join(APP_DATA_DIR, filename),
                    resource_path(os.path.join("assets", filename)),
                    resource_path(filename)
                ]
                for p in paths:
                    if p and os.path.exists(p):
                        pix = QPixmap(p)
                        if not pix.isNull():
                            return pix
                logger.warning(f"Không tìm thấy file logo bên: {filename}")
                return None

            self.left_logo_pixmap = load_img(left_name)
            self.right_logo_pixmap = load_img(right_name)

            self.ui.left_logo.setVisible(self.left_logo_pixmap is not None)
            self.ui.right_logo.setVisible(self.right_logo_pixmap is not None)

            self._update_side_logos_size()
        except Exception:
            logger.exception("Lỗi khi tải logo trái/phải")

    def resizeEvent(self, event):
        try:
            self._update_background_size()
            self._update_side_logos_size()
        except Exception:
            logger.exception("Lỗi trong resizeEvent của MainMenuWindow")
        super().resizeEvent(event)

    def _update_background_size(self):
        if getattr(self, 'cached_bg_pixmap', None):
            try:
                window_size = self.ui.watermark_logo.size()
                scaled_pixmap = self.cached_bg_pixmap.scaled(
                    window_size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation
                )
                self.ui.watermark_logo.setPixmap(scaled_pixmap)
            except Exception:
                logger.exception("Lỗi khi cập nhật kích thước background")

    def _update_side_logos_size(self):
        try:
            target_height = max(100, int(self.height() * 0.25))
            if getattr(self, 'left_logo_pixmap', None):
                scaled = self.left_logo_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
                self.ui.left_logo.setPixmap(scaled)
            if getattr(self, 'right_logo_pixmap', None):
                scaled = self.right_logo_pixmap.scaledToHeight(target_height, Qt.SmoothTransformation)
                self.ui.right_logo.setPixmap(scaled)
        except Exception:
            logger.exception("Lỗi khi cập nhật kích thước logo bên")

    # Map commonly used buttons to top-level attributes for compatibility
    def _attach_buttons(self):
        try:
            self.practice_button = getattr(self.ui, 'practice_button', None)
            self.stats_button = getattr(self.ui, 'stats_button', None)
            self.guide_button = getattr(self.ui, 'guide_button', None)
            self.exit_button = getattr(self.ui, 'exit_button', None)
            self.settings_button = getattr(self.ui, 'settings_button', None)
        except Exception:
            logger.exception("Lỗi khi gán thuộc tính nút trong MainMenuWindow")
