# file: main.py
import os
import sys
import logging
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QThread
# --- BẮT ĐẦU VÙNG THAY ĐỔI: IMPORT THÊM ---
from PySide6.QtGui import QIcon
from utils.resource_path import resource_path
# --- KẾT THÚC VÙNG THAY ĐỔI ---

# Import các lớp cửa sổ và các thành phần chạy ngầm
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

# Cấu hình logging cơ bản (giữ nguyên)
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.getLogger().addHandler(file_handler)
logging.info("--- Application Started ---")


# Hàm check_or_request_license giữ nguyên
def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')

    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f:
            key = f.read().strip()
        if verify_key(key):
            logging.info("License hợp lệ được tìm thấy.")
            return True
        else:
            logging.warning("File license không hợp lệ, đang xóa.")
            os.remove(license_file_path)

    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok:
            return False

        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f:
                f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công! Ứng dụng sẽ khởi động.")
            return True
        else:
            QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ cho máy tính này. Vui lòng thử lại.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.config = self._load_config()
        app_title = self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        self.setStyleSheet("background-color: #2c3e50;")
        logging.info(f"Configuration loaded: {self.config}")
        
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        self.main_menu = MainMenuWindow(self.config)
        self.practice_screen = PracticeWindow(
            worker=self.processing_worker, 
            trigger=self.bt_trigger,
            config=self.config
        )
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
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        
        defaults = {
            "camera_index": 0,
            "yolo_confidence_threshold": 0.75,
            "manage_image_height": 400,
            "labels": {
                "app_title": "PHẦN MỀM KIỂM TRA ĐƯỜNG NGẮM",
                "app_subtitle": "SÚNG TIỂU LIÊN STV",
                "trainee": "Người học",
                "trainee_class": "Đơn vị",
                "trainee_list_title": "Danh sách Người học",
                "trainee_list_header_name": "Họ và Tên",
                "trainee_list_header_class": "Đơn vị",
                "add_trainee_dialog_title": "Thêm Người học Mới",
                "edit_trainee_dialog_title": "Chỉnh sửa thông tin Người học",
                "trainee_name_prompt": "Họ và Tên:",
                "trainee_class_prompt": "Đơn vị:",
                "history_title_prefix": "Lịch sử bắn của"
            }
        }

        try:
            if not os.path.exists(config_path):
                logging.warning(f"File config.json không tồn tại. Tạo file mặc định tại: {config_path}")
                with open(config_path, "w", encoding='utf-8') as f:
                    json.dump(defaults, f, indent=4, ensure_ascii=False)
                return defaults
            
            with open(config_path, "r", encoding='utf-8') as f:
                loaded_config = json.load(f)
                defaults.update(loaded_config)
                return defaults

        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Lỗi khi đọc/tạo file config: {e}. Sử dụng cấu hình mặc định.")
            return defaults
            
    def connect_signals(self):
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)       
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.manage_screen.ui.back_button.clicked.connect(self.show_main_menu)
        self.main_menu.exit_button.clicked.connect(self.close)

        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.finished.connect(self.practice_screen.on_processing_finished)
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)

    def cleanup_before_exit(self):
        print("INFO: Bắt đầu quá trình dọn dẹp ứng dụng...")
        
        if self.bt_trigger:
            self.bt_trigger.stop_global_listener()

        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000):
                self.processing_thread.terminate()
            
        print("INFO: Dọn dẹp hoàn tất.")

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
    app = QApplication(sys.argv)

    # --- BẮT ĐẦU VÙNG THAY ĐỔI: THIẾT LẬP ICON TOÀN CỤC ---
    # 1. Xác định đường dẫn tới file icon bằng resource_path
    icon_path = resource_path("assets/app_icon.ico")
    
    # 2. Tạo đối tượng QIcon
    app_icon = QIcon(icon_path)
    
    # 3. Gán icon cho toàn bộ ứng dụng
    app.setWindowIcon(app_icon)
    # --- KẾT THÚC VÙNG THAY ĐỔI ---

    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()