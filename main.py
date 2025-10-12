# file: main.py
import os
import sys
import logging
import json
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QMessageBox
from PySide6.QtCore import QThread, Slot
from datetime import datetime

from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from gui.windows.competition_menu_window import CompetitionMenuWindow
from gui.windows.competition_window import CompetitionWindow
from gui.windows.setup_competition_window import SetupCompetitionWindow

from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from config import APP_DATA_DIR
from utils.license_manager import verify_key

# --- Cấu hình logging và License (Giữ nguyên) ---
os.makedirs(APP_DATA_DIR, exist_ok=True)
log_file_path = os.path.join(APP_DATA_DIR, "app_log.txt")
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s'))
logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler(), file_handler])
logging.info("--- Application Started ---")

def check_or_request_license() -> bool:
    license_file_path = os.path.join(APP_DATA_DIR, 'license.key')
    if os.path.exists(license_file_path):
        with open(license_file_path, 'r', encoding='utf-8') as f: key = f.read().strip()
        if verify_key(key): logging.info("License hợp lệ được tìm thấy."); return True
        else: logging.warning("File license không hợp lệ, đang xóa."); os.remove(license_file_path)
    while True:
        from PySide6.QtWidgets import QInputDialog
        key, ok = QInputDialog.getText(None, "Yêu cầu Kích hoạt", "Vui lòng nhập License Key:")
        if not ok: return False
        if verify_key(key):
            with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
            QMessageBox.information(None, "Thành công", "Kích hoạt thành công!"); return True
        else: QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ.")

class ApplicationController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Luyện Tập Đường Ngắm Súng Ngắn K54")
        
        self.config = self._load_config()
        self.processing_thread = QThread()
        self.processing_worker = ProcessingWorker(self.config)
        self.bt_trigger = BluetoothTrigger()
        self.processing_worker.moveToThread(self.processing_thread)
        
        # --- THAY ĐỔI: Truyền `self.config` vào các cửa sổ cần thiết ---
        self.main_menu = MainMenuWindow()
        self.practice_screen = PracticeWindow(self.processing_worker, self.bt_trigger, self.config)
        self.manage_screen = ManageWindow(self.config)
        self.competition_menu = CompetitionMenuWindow()
        self.setup_competition_screen = SetupCompetitionWindow()
        self.competition_screen = CompetitionWindow(self.processing_worker, self.bt_trigger, self.config)
        # --- Kết thúc thay đổi ---
        
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)
        self.stacked_widget.addWidget(self.main_menu); self.stacked_widget.addWidget(self.practice_screen)
        self.stacked_widget.addWidget(self.manage_screen); self.stacked_widget.addWidget(self.competition_menu)
        self.stacked_widget.addWidget(self.setup_competition_screen); self.stacked_widget.addWidget(self.competition_screen)
        
        self.connect_signals()
        
        self.processing_thread.start()
        self.bt_trigger.start_global_listener()

    def _load_config(self) -> dict:
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        defaults = {"camera_index": 0, "yolo_confidence_threshold": 0.45, "manage_image_height": 400}
        try:
            if not os.path.exists(config_path):
                with open(config_path, "w", encoding='utf-8') as f: json.dump(defaults, f, indent=4)
                return defaults
            with open(config_path, "r", encoding='utf-8') as f: loaded_config = json.load(f)
            defaults.update(loaded_config)
            return defaults
        except (json.JSONDecodeError, IOError): return defaults

    def connect_signals(self):
        self.main_menu.practice_button.clicked.connect(self.show_practice_screen)
        self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
        self.main_menu.competition_button.clicked.connect(self.show_competition_menu)
        self.main_menu.exit_button.clicked.connect(self.close)
        self.competition_menu.start_button.clicked.connect(self.show_setup_competition_screen)
        self.competition_menu.back_button.clicked.connect(self.show_main_menu)
        self.setup_competition_screen.start_competition_signal.connect(self.start_new_competition)
        self.setup_competition_screen.back_button.clicked.connect(self.show_competition_menu)
        self.practice_screen.back_to_main_menu.connect(self.show_main_menu) 
        self.manage_screen.back_to_main_menu.connect(self.show_main_menu)
        self.competition_screen.back_to_menu_signal.connect(self.show_competition_menu)
        self.practice_screen.request_processing.connect(self.processing_worker.process_image)
        self.competition_screen.request_processing.connect(self.processing_worker.process_image)
        self.processing_worker.practice_finished.connect(self.practice_screen.on_processing_finished)
        self.processing_worker.competition_finished.connect(self.competition_screen.handle_processing_result)
        self.bt_trigger.triggered.connect(self.handle_global_trigger)

    @Slot()
    def handle_global_trigger(self):
        current_widget = self.stacked_widget.currentWidget()
        if current_widget == self.practice_screen:
            self.practice_screen.capture_photo()
        elif current_widget == self.competition_screen:
            self.competition_screen.handle_shot()

    def start_new_competition(self):
        selected_ids = self.setup_competition_screen.get_selected_soldier_ids()
        if not selected_ids:
            QMessageBox.warning(self, "Lỗi", "Không có xạ thủ nào được chọn."); return
        competition_name = f"Cuộc thi ngày {datetime.now().strftime('%d-%m-%Y %H:%M')}"
        db_manager = self.setup_competition_screen.db
        competition_id = db_manager.create_competition(competition_name, selected_ids)
        if competition_id:
            all_soldiers = db_manager.get_all_soldiers()
            selected_participants = [s for s in all_soldiers if s['id'] in selected_ids]
            self.competition_screen.setup_competition(competition_id, selected_participants)
            self.show_competition_screen()
        else: QMessageBox.critical(self, "Lỗi Database", "Không thể tạo cuộc thi mới.")
    
    def cleanup_before_exit(self):
        logging.info("Dọn dẹp ứng dụng...")
        if self.bt_trigger: self.bt_trigger.stop_global_listener()
        if self.processing_thread.isRunning():
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000): self.processing_thread.terminate()
        logging.info("Dọn dẹp hoàn tất.")

    def show_main_menu(self):
        current = self.stacked_widget.currentWidget()
        if hasattr(current, 'shutdown_components'): current.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.main_menu)

    def show_practice_screen(self): 
        self.stacked_widget.setCurrentWidget(self.practice_screen)
        self.practice_screen.start_camera()

    def show_manage_screen(self): 
        self.manage_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.manage_screen)

    def show_competition_menu(self):
        current = self.stacked_widget.currentWidget()
        if hasattr(current, 'shutdown_components'): current.shutdown_components()
        self.stacked_widget.setCurrentWidget(self.competition_menu)

    def show_setup_competition_screen(self): 
        self.setup_competition_screen.load_soldiers()
        self.stacked_widget.setCurrentWidget(self.setup_competition_screen)

    def show_competition_screen(self): 
        self.stacked_widget.setCurrentWidget(self.competition_screen)
        self.competition_screen.start_camera()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    if check_or_request_license():
        controller = ApplicationController()
        app.aboutToQuit.connect(controller.cleanup_before_exit)
        controller.showMaximized()
        sys.exit(app.exec())
    else: sys.exit()