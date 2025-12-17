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
from PySide6.QtCore import QThread
from PySide6.QtGui import QIcon, QFont, QPalette, QColor

# Import các module trong dự án
from utils.resource_path import resource_path
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
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

# --- GLOBAL STYLESHEET (GIAO DIỆN TOÀN CỤC) ---
GLOBAL_STYLESHEET = """
    /* Thiết lập chung cho toàn bộ ứng dụng */
    QWidget {
        color: #ecf0f1;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* Hộp thoại thông báo (QMessageBox) */
    QMessageBox {
        background-color: #2c3e50;
    }
    QMessageBox QLabel {
        color: #ecf0f1;
    }
    QMessageBox QPushButton {
        background-color: #34495e;
        color: white;
        border: 1px solid #5d6d7e;
        border-radius: 4px;
        padding: 5px 15px;
        min-width: 60px;
    }
    QMessageBox QPushButton:hover {
        background-color: #1abc9c;
    }

    /* Ô nhập liệu (Input Dialog, v.v.) */
    QLineEdit {
        background-color: #34495e;
        color: #ecf0f1;
        border: 1px solid #5d6d7e;
        border-radius: 4px;
        padding: 5px;
        selection-background-color: #1abc9c;
    }
    
    /* Combobox (Danh sách chọn) */
    QComboBox {
        background-color: #34495e;
        color: #ecf0f1;
        border: 1px solid #5d6d7e;
        border-radius: 4px;
        padding: 5px;
    }
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    QComboBox QAbstractItemView {
        background-color: #2c3e50;
        color: #ecf0f1;
        selection-background-color: #1abc9c;
        border: 1px solid #5d6d7e;
    }
    
    /* Scrollbar (Thanh cuộn) */
    QScrollBar:vertical {
        border: none;
        background: #2c3e50;
        width: 10px;
        margin: 0px;
    }
    QScrollBar::handle:vertical {
        background: #5d6d7e;
        min-height: 20px;
        border-radius: 5px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
"""

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    
    # Kiểm tra nếu file license đã tồn tại
    if os.path.exists(license_file_path):
        try:
            with open(license_file_path, 'r', encoding='utf-8') as f:
                key = f.read().strip()
            if verify_key(key):
                logging.info("License hợp lệ.")
                return True
            else:
                logging.warning("License không hợp lệ hoặc đã hết hạn.")
                os.remove(license_file_path) # Xóa file lỗi để nhập lại
        except Exception as e:
            logging.error(f"Lỗi đọc file license: {e}")

    # Nếu chưa có hoặc không hợp lệ, yêu cầu nhập mới
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key để tiếp tục:")
        if not ok:
            return False # Người dùng ấn Cancel -> Thoát app
        
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
        
        # Cài đặt tiêu đề cửa sổ từ config
        app_title = self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        
        # Thiết lập màu nền chính cho Window container
        self.setStyleSheet("background-color: #2c3e50;")
        
        # Khởi tạo các thành phần xử lý ngầm
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        # Khởi tạo các màn hình giao diện
        self.main_menu = MainMenuWindow(self.config)
        self.practice_screen = PracticeWindow(
            worker=self.processing_worker, 
            trigger=self.bt_trigger,
            config=self.config
        )
        self.manage_screen = ManageWindow(self.config)
        
        # Stacked Widget để chuyển đổi giữa các màn hình
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen)

        self.connect_signals()
        
        # Bắt đầu luồng xử lý
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()
    
    def _load_config(self) -> dict:
        config_filename = "config.json"
        dest_path = os.path.join(APP_DATA_DIR, config_filename)
        
        # Nếu config chưa có trong AppData, copy từ source
        if not os.path.exists(dest_path):
            source_path = resource_path(config_filename)
            if os.path.exists(source_path):
                try:
                    shutil.copyfile(source_path, dest_path)
                    logging.info(f"Đã khởi tạo config mặc định tại: {dest_path}")
                except Exception as e:
                    logging.error(f"Lỗi khởi tạo config: {e}")
        
        # Đọc file config
        if os.path.exists(dest_path):
            try:
                with open(dest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"Lỗi đọc config.json: {e}")
        return {}

    def _ensure_assets_are_in_appdata(self):
        """
        Đảm bảo Model và 2 file Logo tồn tại trong AppData để config có thể đọc được.
        """
        # 1. Đảm bảo thư mục assets tồn tại trong AppData
        dest_assets_dir = os.path.join(APP_DATA_DIR, "assets")
        os.makedirs(dest_assets_dir, exist_ok=True)

        # --- PHẦN SAO CHÉP MODEL ---
        model_filename = self.config.get("yolo_model_name")
        if model_filename:
            dest_model_path = os.path.join(APP_DATA_DIR, model_filename)
            if not os.path.exists(dest_model_path):
                source_model_path = resource_path(os.path.join("assets", "models", model_filename))
                if os.path.exists(source_model_path):
                    try:
                        shutil.copyfile(source_model_path, dest_model_path)
                        logging.info(f"Đã sao chép model '{model_filename}' vào AppData.")
                    except Exception as e:
                        logging.error(f"Lỗi sao chép model: {e}")

        # --- PHẦN SAO CHÉP LOGO (CHỈ 2 FILE QUAN TRỌNG) ---
        target_logos = ["logo_left.png", "logo_right.png"]

        for filename in target_logos:
            dest_path = os.path.join(dest_assets_dir, filename)
            
            # Chỉ copy nếu file chưa tồn tại (để tránh ghi đè logo user đã đổi)
            if not os.path.exists(dest_path):
                source_path = resource_path(os.path.join("assets", filename))
                
                if os.path.exists(source_path):
                    try:
                        shutil.copyfile(source_path, dest_path)
                        logging.info(f"Đã sao chép '{filename}' sang AppData/assets.")
                    except Exception as e:
                        logging.error(f"Lỗi khi copy {filename}: {e}")
                else:
                    logging.debug(f"Không tìm thấy file gốc '{filename}' trong assets để sao chép.")

    def connect_signals(self):
        # Navigation
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)       
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.manage_screen.ui.back_button.clicked.connect(self.show_main_menu)
        self.main_menu.exit_button.clicked.connect(self.close)

        # Logic kết nối giữa Trigger -> GUI -> Worker
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.finished.connect(self.practice_screen.on_processing_finished)
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)

    def cleanup_before_exit(self):
        logging.info("INFO: Bắt đầu quá trình dọn dẹp ứng dụng...")
        
        if self.bt_trigger:
            self.bt_trigger.stop_global_listener()

        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000):
                self.processing_thread.terminate()
            
        logging.info("INFO: Dọn dẹp hoàn tất.")

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

if __name__ == '__main__':
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    
    # --- ÁP DỤNG STYLE TOÀN CỤC (FUSION + CUSTOM CSS) ---
    app.setStyle("Fusion") 
    app.setStyleSheet(GLOBAL_STYLESHEET)
    
    # Font chữ mặc định
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Icon ứng dụng
    icon_path = resource_path("assets/app_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    # Kiểm tra bản quyền trước khi chạy
    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()