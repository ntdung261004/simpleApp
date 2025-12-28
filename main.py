# file: main.py
import os
import sys
import logging
import json
import shutil
import multiprocessing
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QInputDialog, 
    QMessageBox, QProxyStyle, QStyleFactory
)
from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QIcon, QFont, QPalette, QColor, QDesktopServices

# Import các module trong dự án
from utils.resource_path import resource_path
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from gui.windows.guide_window import GuideWindow # <--- MỚI: Import GuideWindow
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

# --- CẤU HÌNH LOGGING ---
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)

logging.info("--- Application Started ---")

# --- GLOBAL STYLESHEET ---
GLOBAL_STYLESHEET = """
    QWidget { color: #ecf0f1; font-family: 'Segoe UI', sans-serif; }
    QMessageBox { background-color: #2c3e50; }
    QMessageBox QLabel { color: #ecf0f1; }
    QMessageBox QPushButton { background-color: #34495e; color: white; border: 1px solid #5d6d7e; border-radius: 4px; padding: 5px 15px; min-width: 60px; }
    QMessageBox QPushButton:hover { background-color: #1abc9c; }
    QLineEdit { background-color: #34495e; color: #ecf0f1; border: 1px solid #5d6d7e; border-radius: 4px; padding: 5px; selection-background-color: #1abc9c; }
    QComboBox { background-color: #34495e; color: #ecf0f1; border: 1px solid #5d6d7e; border-radius: 4px; padding: 5px; }
    QComboBox::drop-down { border: none; width: 20px; }
    QComboBox QAbstractItemView { background-color: #2c3e50; color: #ecf0f1; selection-background-color: #1abc9c; border: 1px solid #5d6d7e; }
    QScrollBar:vertical { border: none; background: #2c3e50; width: 10px; margin: 0px; }
    QScrollBar::handle:vertical { background: #5d6d7e; min-height: 20px; border-radius: 5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
"""

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        try:
            with open(license_file_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
            if verify_key(key):
                logging.info("License hợp lệ.")
                return True
            else:
                logging.warning("License không hợp lệ hoặc đã hết hạn.")
                os.remove(license_file_path) 
        except Exception as e:
            logging.error(f"Lỗi đọc file license: {e}")

    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key để tiếp tục:")
        if not ok: return False 
        if verify_key(key):
            try:
                with open(license_file_path, 'w', encoding='utf-8') as f:
                    f.write(key)
                QMessageBox.information(None, "Thành công", "Kích hoạt phần mềm thành công!")
                return True
            except Exception as e:
                QMessageBox.critical(None, "Lỗi", f"Không thể lưu license: {e}")
                return False
        else:
            QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ. Vui lòng kiểm tra lại.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self._ensure_assets_are_in_appdata()
        
        app_title = self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        self.setStyleSheet("background-color: #2c3e50;")
        
        # --- Worker & Trigger ---
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        # --- Khởi tạo các màn hình ---
        self.main_menu = MainMenuWindow(self.config)
        self.practice_screen = PracticeWindow(worker=self.processing_worker, trigger=self.bt_trigger, config=self.config)
        self.manage_screen = ManageWindow(self.config)
        self.guide_screen = GuideWindow() # <--- MỚI: Khởi tạo màn hình hướng dẫn
        
        # --- Stacked Widget ---
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)       # index 0
        self.stacked_widget.addWidget(self.practice_screen) # index 1
        self.stacked_widget.addWidget(self.manage_screen)   # index 2
        self.stacked_widget.addWidget(self.guide_screen)    # index 3

        self.connect_signals()
        
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()
    
    def _load_config(self) -> dict:
        config_filename = "config.json"
        dest_path = os.path.join(APP_DATA_DIR, config_filename)
        if not os.path.exists(dest_path):
            source_path = resource_path(config_filename)
            if os.path.exists(source_path):
                shutil.copyfile(source_path, dest_path)
        if os.path.exists(dest_path):
            with open(dest_path, 'r', encoding='utf-8') as f: return json.load(f)
        return {}

    def _ensure_assets_are_in_appdata(self):
        dest_assets_dir = os.path.join(APP_DATA_DIR, "assets")
        os.makedirs(dest_assets_dir, exist_ok=True)
        # Copy model & logo logic (Giữ nguyên)
        pass 

    def connect_signals(self):
        # Menu -> Các màn hình khác
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)       
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        
        # Menu -> Hướng dẫn (MỚI)
        self.main_menu.guide_button.clicked.connect(self.show_guide_screen)

        # Các màn hình con -> Quay lại Menu
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.manage_screen.ui.back_button.clicked.connect(self.show_main_menu)
        self.guide_screen.request_back_menu.connect(self.show_main_menu) # (MỚI)

        # Thoát
        self.main_menu.exit_button.clicked.connect(self.close)

        # Worker Logic
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.finished.connect(self.practice_screen.on_processing_finished)
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)

    def cleanup_before_exit(self):
        if self.bt_trigger: self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait(3000)

    def show_main_menu(self):
        if self.stacked_widget.currentWidget() == self.practice_screen:
            self.practice_screen.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self):
        self.practice_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        
    def show_manage_screen(self):
        self.manage_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.manage_screen)

    def show_guide_screen(self):
        # Load lại file PDF mỗi khi mở để đảm bảo cập nhật nếu file thay đổi
        self.guide_screen.load_pdf() 
        self.stacked_widget.setCurrentWidget(self.guide_screen)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 
    app.setStyleSheet(GLOBAL_STYLESHEET)
    app.setFont(QFont("Segoe UI", 10))
    app.setWindowIcon(QIcon(resource_path("assets/app_icon.ico")))

    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()