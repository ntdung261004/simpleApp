# Thay thế TOÀN BỘ file main.py
import os
import sys
import logging
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

# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')

# Thiết lập logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')

# Tạo và cấu hình FileHandler để ghi log vào file trong AppData
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.getLogger().addHandler(file_handler)

logging.info("--- Application Started ---")

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
            # Vòng lặp sẽ tiếp tục để người dùng nhập lại
class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")

        # --- 1. Tạo các thành phần chạy ngầm TRƯỚC TIÊN ---
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker()
        self.bt_trigger = BluetoothTrigger()
        
        self.processing_thread.setObjectName("ProcessingThread")
        self.processing_worker.moveToThread(self.processing_thread)
        
        # --- 2. Tạo các cửa sổ giao diện ---
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow(
            worker=self.processing_worker, 
            trigger=self.bt_trigger
        )
        self.manage_screen = ManageWindow()

        # --- 3. Quản lý các màn hình bằng QStackedWidget ---
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen)

        # --- 4. Kết nối các tín hiệu ---
        self.connect_signals()
        
        # Bắt đầu các luồng chạy ngầm
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

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

    # --- Các hàm hiển thị cửa sổ ---
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
    # Bước 1: Tạo QApplication MỘT LẦN DUY NHẤT
    app = QApplication(sys.argv)

    # Bước 2: Gọi hàm kiểm tra license. Hàm này sẽ sử dụng QApplication đã tồn tại
    if check_or_request_license():
        # Bước 3: Nếu license hợp lệ, tạo và chạy ứng dụng chính
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showFullScreen()
        sys.exit(app.exec())
    else:
        # Nếu người dùng nhấn Cancel ở hộp thoại license, ứng dụng sẽ thoát êm đẹp
        sys.exit()