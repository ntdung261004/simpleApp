# file: main.py
import os
import sys
import logging
import json
import shutil
import traceback # <<< THÊM MỚI để ghi log lỗi chi tiết
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import QThread, Slot, QTimer
from datetime import datetime

from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from gui.windows.competition_menu_window import CompetitionMenuWindow
from gui.windows.competition_window import CompetitionWindow
from gui.windows.setup_competition_window import SetupCompetitionWindow
from gui.windows.saved_competitions_window import SavedCompetitionsWindow
from gui.windows.competition_stats_window import CompetitionStatsWindow

from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key
from utils.resource_path import resource_path

os.makedirs(APP_DATA_DIR, exist_ok=True)
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), logging.FileHandler(log_file_path, 'a', 'utf-8')], format='%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')
logging.info("--- Application Started ---")

# === BẮT ĐẦU VÙNG THÊM MỚI: GHI LOG LỖI TOÀN CỤC ===
def global_exception_hook(exctype, value, tb):
    """Bẫy và ghi lại tất cả các lỗi không được xử lý trong ứng dụng."""
    error_message = "".join(traceback.format_exception(exctype, value, tb))
    logging.critical(f"LỖI KHÔNG XÁC ĐỊNH GÂY SẬP ỨNG DỤNG:\n{error_message}")
    # Hiển thị thông báo lỗi cho người dùng
    QMessageBox.critical(
        None,
        "Lỗi nghiêm trọng",
        "Ứng dụng đã gặp một lỗi không mong muốn và cần phải đóng.\n"
        f"Vui lòng kiểm tra file app_log.txt trong thư mục:\n{APP_DATA_DIR}\n\n"
        f"Chi tiết lỗi: {value}"
    )
    sys.exit(1)

# Gán hàm xử lý lỗi cho hệ thống
sys.excepthook = global_exception_hook
# === KẾT THÚC VÙNG THÊM MỚI ===

def check_or_request_license() -> bool:
    license_file = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file):
        with open(license_file, 'r') as f: key = f.read().strip()
        if verify_key(key): logging.info("License hợp lệ."); return True
        os.remove(license_file)
    from PySide6.QtWidgets import QInputDialog
    while True:
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file, 'w') as f: f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công!"); return True
        QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Luyện Tập và Kiểm Tra Bắn Súng K54")
        self.config = self._load_config()
        
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        self.processing_worker.moveToThread(self.processing_thread)
        
        self.is_on_cooldown = False
        self.trigger_cooldown_timer = QTimer(self)
        self.trigger_cooldown_timer.setSingleShot(True)
        self.trigger_cooldown_timer.timeout.connect(self._reset_cooldown)

        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow(self.processing_worker, self.bt_trigger, self.config)
        self.manage_screen = ManageWindow(self.config)
        self.competition_menu = CompetitionMenuWindow()
        self.setup_competition_screen = SetupCompetitionWindow()
        self.competition_screen = CompetitionWindow(self.processing_worker, self.bt_trigger, self.config)
        self.saved_competitions_screen = SavedCompetitionsWindow()
        self.competition_stats_screen = CompetitionStatsWindow()
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        all_screens = [
            self.main_menu, self.practice_screen, self.manage_screen, 
            self.competition_menu, self.setup_competition_screen, 
            self.competition_screen, self.saved_competitions_screen,
            self.competition_stats_screen
        ]
        for widget in all_screens:
            self.stacked_widget.addWidget(widget)
        
        self._connect_signals()
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

    def _load_config(self) -> dict:
        dest_config_path = os.path.join(APP_DATA_DIR, "config.json")
        defaults = {"camera_index": 1, "yolo_confidence_threshold": 0.35, "yolo_model_path": "assets/models/K54v2.pt"}

        if not os.path.exists(dest_config_path):
            try:
                source_config_path = resource_path("config.json")
                if os.path.exists(source_config_path):
                    shutil.copyfile(source_config_path, dest_config_path)
                    logging.info(f"Đã sao chép config.json mặc định vào {APP_DATA_DIR}")
            except Exception as e:
                logging.error(f"Không thể sao chép config.json: {e}")

        try:
            with open(dest_config_path, "r") as f:
                loaded_config = json.load(f)
            defaults.update(loaded_config)
        except (IOError, json.JSONDecodeError):
            logging.warning(f"Không thể đọc {dest_config_path}. Sử dụng cấu hình mặc định.")
        
        config = defaults

        model_relative_path = config.get("yolo_model_path")
        if model_relative_path:
            dest_model_path = os.path.join(APP_DATA_DIR, model_relative_path)
            os.makedirs(os.path.dirname(dest_model_path), exist_ok=True)

            if not os.path.exists(dest_model_path):
                try:
                    source_model_path = resource_path(model_relative_path)
                    if os.path.exists(source_model_path):
                        shutil.copyfile(source_model_path, dest_model_path)
                        logging.info(f"Đã sao chép model mặc định vào {os.path.dirname(dest_model_path)}")
                except Exception as e:
                    logging.error(f"Không thể sao chép file model: {e}")
        
        return config

    def _connect_signals(self):
        # Navigation
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.main_menu.competition_button.clicked.connect(self.show_competition_menu)
        self.main_menu.exit_button.clicked.connect(self.close)
        self.practice_screen.back_to_main_menu.connect(self.show_main_menu)
        self.manage_screen.back_to_main_menu.connect(self.show_main_menu)
        self.competition_menu.start_button.clicked.connect(self.show_setup_competition_screen)
        self.competition_menu.saved_button.clicked.connect(self.show_saved_competitions_screen)
        self.competition_menu.stats_button.clicked.connect(self.show_competition_stats_screen)
        self.competition_menu.back_button.clicked.connect(self.show_main_menu)
        self.setup_competition_screen.start_competition_signal.connect(self.start_new_competition)
        self.setup_competition_screen.ui.back_button.clicked.connect(self.show_competition_menu)
        self.competition_screen.back_to_menu_signal.connect(self.show_competition_menu)
        self.saved_competitions_screen.back_to_menu_signal.connect(self.show_competition_menu)
        self.saved_competitions_screen.resume_competition_signal.connect(self.resume_competition)
        self.competition_stats_screen.back_to_menu_signal.connect(self.show_competition_menu)

        # Core processing logic
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.competition_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.practice_finished.connect(self.practice_screen.on_processing_finished)
        self.processing_worker.competition_finished.connect(self.competition_screen.handle_processing_result)
        
        # Trigger and Threading
        self.bt_trigger.triggered.connect(self.handle_global_trigger)
    
    @Slot()
    def _reset_cooldown(self):
        self.is_on_cooldown = False
    
    @Slot()
    def handle_global_trigger(self):
        if self.is_on_cooldown:
            return

        self.is_on_cooldown = True
        self.trigger_cooldown_timer.start(500)
        
        current_widget = self.stacked_widget.currentWidget()
        if isinstance(current_widget, PracticeWindow):
            current_widget.capture_photo()
        elif isinstance(current_widget, CompetitionWindow):
            current_widget.handle_shot()

    @Slot(str, list)
    def start_new_competition(self, competition_name: str, selected_soldier_ids: list):
        db_manager = self.setup_competition_screen.db
        all_soldiers = db_manager.get_all_soldiers()
        selected_participants = [s for s in all_soldiers if s['id'] in selected_soldier_ids]
        competition_id = db_manager.create_competition(competition_name, [p['id'] for p in selected_participants])
        if competition_id:
            self.competition_screen.setup_competition(competition_id, competition_name, selected_participants)
            self.show_competition_screen()
        else:
            QMessageBox.critical(self, "Lỗi Database", "Không thể tạo cuộc thi mới. Tên cuộc thi có thể đã tồn tại.")

    @Slot(dict)
    def resume_competition(self, state_data: dict):
        self.competition_screen.load_from_state(state_data)
        self.show_competition_screen()

    def cleanup_before_exit(self):
        logging.info("Dọn dẹp ứng dụng...")
        if self.bt_trigger: self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning(): self.processing_thread.quit(); self.processing_thread.wait(3000)
        logging.info("Dọn dẹp hoàn tất.")

    def _switch_screen(self, target_widget):
        current = self.stacked_widget.currentWidget()
        if hasattr(current, 'shutdown_components'): current.shutdown_components()
        self.stacked_widget.setCurrentWidget(target_widget)
        if hasattr(target_widget, 'start_camera'): target_widget.start_camera()

    def show_main_menu(self): self._switch_screen(self.main_menu)
    def show_practice_screen(self): self._switch_screen(self.practice_screen)
    def show_competition_screen(self): self._switch_screen(self.competition_screen)
    def show_competition_menu(self): self._switch_screen(self.competition_menu)
    
    def show_manage_screen(self): 
        self._switch_screen(self.manage_screen)
        self.manage_screen.load_soldiers()

    def show_setup_competition_screen(self): 
        self.setup_competition_screen.reset_form()
        self._switch_screen(self.setup_competition_screen)
        self.setup_competition_screen.load_soldiers()

    def show_saved_competitions_screen(self):
        self._switch_screen(self.saved_competitions_screen)
        self.saved_competitions_screen.enter_view()

    def show_competition_stats_screen(self):
        self._switch_screen(self.competition_stats_screen)
        self.competition_stats_screen.enter_view()

    def closeEvent(self, event): self.cleanup_before_exit(); super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        controller = ApplicationController()
        controller.showMaximized()
        sys.exit(app.exec())