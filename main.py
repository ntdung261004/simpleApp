# file: main.py
import os
import sys
import logging
import json
import shutil
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QMessageBox
from PySide6.QtCore import QThread
from PySide6.QtGui import QIcon
from utils.resource_path import resource_path

from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
root_logger = logging.getLogger(); root_logger.setLevel(logging.INFO)
fh = logging.FileHandler(log_file_path, encoding='utf-8'); fh.setLevel(logging.INFO)
root_logger.addHandler(fh)

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f:
            if verify_key(f.read().strip()): return True
            else: os.remove(license_file_path)
    while True:
        key, ok = QInputDialog.getText(None, "Kích hoạt", "Nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
            return True
        else: QMessageBox.warning(None, "Lỗi", "Key không hợp lệ.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = self._load_config()
        self._ensure_assets()
        self.setWindowTitle(self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng"))
        self.setStyleSheet("background-color: #2c3e50;")
        
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        self.main_menu = MainMenuWindow(self.config)
        self.practice_screen = PracticeWindow(self.processing_worker, self.bt_trigger, self.config)
        self.manage_screen = ManageWindow(self.config)
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen)

        self.connect_signals()
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()
    
    def _load_config(self) -> dict:
        config_filename = "config.json"
        dest_path = os.path.join(APP_DATA_DIR, config_filename)
        if not os.path.exists(dest_path):
            src = resource_path(config_filename)
            if os.path.exists(src): shutil.copyfile(src, dest_path)
        if os.path.exists(dest_path):
            with open(dest_path, 'r', encoding='utf-8') as f: return json.load(f)
        return {}

    def _ensure_assets(self):
        model_filename = self.config.get("yolo_model_name")
        if model_filename:
            dest = os.path.join(APP_DATA_DIR, model_filename)
            if not os.path.exists(dest):
                src = resource_path(os.path.join("assets", "models", model_filename))
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    shutil.copyfile(src, dest)

    def connect_signals(self):
        self.main_menu.practice_button.clicked.connect(self.show_practice)       
        self.main_menu.stats_button.clicked.connect(self.show_manage)
        
        self.practice_screen.back_to_menu_signal.connect(self.show_menu)
        
        # --- KẾT NỐI TÍN HIỆU QUAY VỀ TỪ QUẢN LÝ ---
        self.manage_screen.back_to_menu_signal.connect(self.show_menu)
        # Nút con "Quay lại Menu" trong các trang con cũng gọi show_menu
        self.manage_screen.ui.btn_back_to_menu.clicked.connect(self.show_menu)
        # -------------------------------------------
        
        self.main_menu.exit_button.clicked.connect(self.close)
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)

    def cleanup_before_exit(self):
        if self.bt_trigger: self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            self.processing_thread.wait(3000)

    def show_menu(self):
        if self.stacked_widget.currentWidget() == self.practice_screen:
            self.practice_screen.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice(self):
        self.practice_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        
    def show_manage(self):
        self.manage_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.manage_screen)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_path = resource_path("assets/app_icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else: sys.exit()