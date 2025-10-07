# Thay thế TOÀN BỘ file main.py
import os
import sys
import logging
import json # <<< THÊM MỚI: Import module json
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QThread

# Import các lớp cửa sổ và các thành phần chạy ngầm
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

# Cấu hình logging cơ bản (giữ nguyên)
# ... (Phần logging của bạn giữ nguyên, không cần thay đổi)
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.getLogger().addHandler(file_handler)
logging.info("--- Application Started ---")


# Hàm check_or_request_license giữ nguyên
def check_or_request_license() -> bool:
    """
    Kiểm tra license. Trả về True nếu hợp lệ, False nếu không.
    Hàm này KHÔNG tự tạo QApplication nữa.
    """
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

    # Nếu không có file hoặc key sai, yêu cầu nhập key mới
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok:
            return False # Người dùng nhấn Cancel

        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f:
                f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công! Ứng dụng sẽ khởi động.")
            return True # Kích hoạt thành công
        else:
            QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ cho máy tính này. Vui lòng thử lại.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Tập Luyện Đường Ngắm Súng Ngắn K54 ")

        # --- BẮT ĐẦU THAY ĐỔI ---

        # 1. Tải cấu hình từ file config.json
        self.config = self._load_config()
        logging.info(f"Configuration loaded: {self.config}")
        
        # 2. Tạo các thành phần chạy ngầm và truyền config vào
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config) # << Truyền config
        self.bt_trigger = BluetoothTrigger()
        
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        # 3. Tạo các cửa sổ giao diện và truyền config vào
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow(
            worker=self.processing_worker, 
            trigger=self.bt_trigger
        )
        self.manage_screen = ManageWindow(self.config) # << Truyền config

        # --- KẾT THÚC THAY ĐỔI ---

        # 4. Quản lý các màn hình bằng QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen)

        # 5. Kết nối các tín hiệu
        self.connect_signals()
        
        # Bắt đầu các luồng chạy ngầm
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

    # --- HÀM MỚI: ĐỂ TẢI CONFIG ---
    def _load_config(self) -> dict:
        """
        Tải file config.json từ thư mục AppData.
        Nếu không có file, sẽ tạo file mặc định.
        Đảm bảo các giá trị mặc định luôn tồn tại.
        """
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        
        # Các giá trị mặc định để ứng dụng không bị lỗi nếu thiếu
        defaults = {
            "camera_index": 0,
            "yolo_confidence_threshold": 0.45,
            "manage_image_height": 400
        }

        try:
            if not os.path.exists(config_path):
                logging.warning(f"File config.json không tồn tại. Tạo file mặc định tại: {config_path}")
                with open(config_path, "w", encoding='utf-8') as f:
                    json.dump(defaults, f, indent=4)
                return defaults
            
            with open(config_path, "r", encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Hợp nhất config đã tải với mặc định để đảm bảo đủ khóa
                defaults.update(loaded_config)
                return defaults

        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Lỗi khi đọc/tạo file config: {e}. Sử dụng cấu hình mặc định.")
            return defaults

    # Các hàm còn lại giữ nguyên
    def connect_signals(self):
        # Điều hướng
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)       
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.manage_screen.ui.back_button.clicked.connect(self.show_main_menu)
        self.main_menu.exit_button.clicked.connect(self.close)

        # Tín hiệu xử lý
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.finished.connect(self.practice_screen.on_processing_finished)
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)

    def cleanup_before_exit(self):
        """Hàm dọn dẹp trung tâm, được gọi bởi aboutToQuit."""
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

    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()