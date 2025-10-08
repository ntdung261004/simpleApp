# file: main.py
import os
import sys
import logging
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QThread
from datetime import datetime

# Import các lớp cửa sổ và các thành phần chạy ngầm
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from gui.windows.competition_menu_window import CompetitionMenuWindow
from gui.windows.competition_window import CompetitionWindow
from gui.windows.setup_competition_window import SetupCompetitionWindow # Import màn hình mới

from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

# --- Cấu hình logging ---
os.makedirs(APP_DATA_DIR, exist_ok=True)
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[
    logging.StreamHandler(), # In ra console
    file_handler         # Ghi vào file
])
logging.info("--- Application Started ---")


# --- Hàm kiểm tra License ---
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
    """Lớp điều khiển chính, quản lý tất cả các cửa sổ và luồng dữ liệu."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Luyện Tập Đường Ngắm Súng Ngắn K54")
        
        # 1. Tải cấu hình
        self.config = self._load_config()
        logging.info(f"Configuration loaded: {self.config}")
        
        # 2. Khởi tạo các thành phần chạy ngầm
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        self.processing_worker.moveToThread(self.processing_thread)
        
        # 3. Khởi tạo các cửa sổ giao diện
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow(self.processing_worker, self.bt_trigger)
        self.manage_screen = ManageWindow(self.config)
        self.competition_menu = CompetitionMenuWindow()
        self.setup_competition_screen = SetupCompetitionWindow()
        self.competition_screen = CompetitionWindow(self.processing_worker, self.bt_trigger)

        # 4. Quản lý các màn hình bằng QStackedWidget
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen)
        self.stacked_widget.addWidget(self.competition_menu)
        self.stacked_widget.addWidget(self.setup_competition_screen)
        self.stacked_widget.addWidget(self.competition_screen)

        # 5. Kết nối các tín hiệu
        self.connect_signals()
        
        # 6. Bắt đầu các luồng chạy ngầm
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

    def _load_config(self) -> dict:
        """Tải file config.json, tạo file mặc định nếu chưa có."""
        config_path = os.path.join(APP_DATA_DIR, "config.json")
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
                defaults.update(loaded_config)
                return defaults
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Lỗi khi đọc/tạo file config: {e}. Sử dụng cấu hình mặc định.")
            return defaults

    def connect_signals(self):
        """Kết nối tất cả các sự kiện click chuột và tín hiệu giữa các thành phần."""
        # --- Menu chính ---
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.main_menu.competition_button.clicked.connect(self.show_competition_menu)
        self.main_menu.exit_button.clicked.connect(self.close)

        # --- Menu Thi đấu ---
        self.competition_menu.start_button.clicked.connect(self.show_setup_competition_screen)
        self.competition_menu.saved_button.clicked.connect(self.feature_not_implemented)
        self.competition_menu.stats_button.clicked.connect(self.feature_not_implemented)
        self.competition_menu.back_button.clicked.connect(self.show_main_menu)
        
        # --- Màn hình Thiết lập Thi đấu ---
        self.setup_competition_screen.start_competition_button.clicked.connect(self.start_new_competition)
        self.setup_competition_screen.back_button.clicked.connect(self.show_competition_menu)
        
        # --- Nút "Back" của các màn hình khác ---
        self.practice_screen.gui.back_button.clicked.connect(self.show_main_menu)
        self.manage_screen.ui.back_button.clicked.connect(self.show_main_menu)
        self.competition_screen.gui.back_button.clicked.connect(self.show_competition_menu)
       
        # --- Tín hiệu xử lý ---
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.finished.connect(self.practice_screen.on_processing_finished)
        self.bt_trigger.triggered.connect(self.practice_screen.capture_photo)
        # (Lưu ý: Tín hiệu của màn hình Thi đấu sẽ được kết nối sau)

    def cleanup_before_exit(self):
        """Hàm dọn dẹp trung tâm, được gọi bởi aboutToQuit."""
        logging.info("Bắt đầu quá trình dọn dẹp ứng dụng...")
        if self.bt_trigger:
            self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000):
                self.processing_thread.terminate()
        logging.info("Dọn dẹp hoàn tất.")

    # === CÁC HÀM ĐIỀU HƯỚNG MÀN HÌNH ===
    def show_main_menu(self):
        """Hiển thị menu chính, tắt camera nếu cần."""
        current = self.stacked_widget.currentWidget()
        if hasattr(current, 'shutdown_components'):
            current.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self):
        """Chuyển sang màn hình luyện tập."""
        self.practice_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        
    def show_manage_screen(self):
        """Chuyển sang màn hình quản lý."""
        self.manage_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.manage_screen)

    def show_competition_menu(self):
        """Chuyển sang menu của chức năng thi đấu."""
        self.stacked_widget.setCurrentWidget(self.competition_menu)

    def show_setup_competition_screen(self):
        """Chuyển sang màn hình thiết lập thi đấu."""
        self.setup_competition_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.setup_competition_screen)

    def start_new_competition(self):
        """
        Xử lý logic khi bắt đầu một cuộc thi mới: tạo cuộc thi trong DB,
        lấy thông tin người tham gia và truyền sang màn hình thi đấu.
        """
        selected_ids = self.setup_competition_screen.get_selected_soldier_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Chưa chọn người bắn", "Vui lòng chọn ít nhất một người để bắt đầu thi đấu.")
            return
            
        competition_name = f"Cuộc thi ngày {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        db_manager = self.setup_competition_screen.db
        competition_id = db_manager.create_competition(competition_name, selected_ids)
        
        if competition_id:
            all_soldiers = db_manager.get_all_soldiers()
            selected_participants = [s for s in all_soldiers if s['id'] in selected_ids]
            
            self.competition_screen.setup_competition(competition_id, selected_participants)
            
            logging.info(f"Đã tạo cuộc thi ID {competition_id}, chuẩn bị chuyển sang màn hình bắn.")
            self.show_competition_screen()
        else:
            QMessageBox.critical(self, "Lỗi Database", "Không thể tạo cuộc thi mới. Vui lòng kiểm tra log.")

    def show_competition_screen(self):
        """Chuyển sang màn hình thi đấu chính (có camera)."""
        self.competition_screen.start_camera()
        self.stacked_widget.setCurrentWidget(self.competition_screen)
        
    def feature_not_implemented(self):
        """Thông báo cho các tính năng chưa được xây dựng."""
        QMessageBox.information(self, "Thông báo", "Chức năng này đang được phát triển.")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit()