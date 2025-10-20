# file: main.py
import os
import sys
import logging
import json
import shutil # <<< THÊM MỚI
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QThread
from PySide6.QtGui import QIcon
from utils.resource_path import resource_path

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
        
        self.config = self._load_config() # Sẽ gọi hàm đã được sửa đổi
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
    
    # --- BẮT ĐẦU VÙNG SỬA ĐỔI: VIẾT LẠI HOÀN TOÀN HÀM _load_config ---
    def _load_config(self) -> dict:
        """
        Tải file config.json. Chỉ sao chép file gốc vào AppData nếu nó chưa tồn tại.
        Điều này giúp bảo toàn các thay đổi của người dùng.
        """
        config_filename = "config.json"
        dest_path = os.path.join(APP_DATA_DIR, config_filename)

        # Chỉ sao chép file config gốc nếu file trong AppData chưa tồn tại
        if not os.path.exists(dest_path):
            logging.info(f"'{config_filename}' không tìm thấy trong AppData. Sao chép file mặc định.")
            source_path = resource_path(config_filename)
            if os.path.exists(source_path):
                try:
                    shutil.copyfile(source_path, dest_path)
                    logging.info(f"Đã sao chép thành công config mặc định vào AppData.")
                except (IOError, shutil.SameFileError) as e:
                    logging.error(f"Không thể sao chép file config mặc định: {e}")
            else:
                logging.error(f"Lỗi nghiêm trọng: Không tìm thấy file config gốc tại '{source_path}'.")

        # Bây giờ, tiến hành đọc file config từ AppData (dù nó vừa được tạo hay đã có sẵn)
        if os.path.exists(dest_path):
            try:
                with open(dest_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logging.error(f"Lỗi khi đọc config từ AppData: {e}")
        
        QMessageBox.critical(None, "Lỗi nghiêm trọng", "Không thể tải file cấu hình (config.json). Ứng dụng có thể không hoạt động đúng.")
        return {}
     
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

    icon_path = resource_path("assets/app_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)

    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()