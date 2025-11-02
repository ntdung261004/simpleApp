# file: main.py
import os
import sys
import traceback

# =============================================================================
# === BẪY LỖI SIÊU SỚM (CRITICAL ERROR TRAP) ===
# Ghi lại lỗi xảy ra ở tầng import trước khi logging kịp khởi động.
# =============================================================================
# Sử dụng user_data_dir một cách an toàn
try:
    from platformdirs import user_data_dir
    APP_DATA_DIR_FOR_ERROR = user_data_dir("TrainingK54", "LTSoftware")
    os.makedirs(APP_DATA_DIR_FOR_ERROR, exist_ok=True)
    error_file_path = os.path.join(APP_DATA_DIR_FOR_ERROR, "critical_error.txt")
except Exception as e:
    # Nếu ngay cả platformdirs cũng lỗi, dùng thư mục tạm
    import tempfile
    APP_DATA_DIR_FOR_ERROR = tempfile.gettempdir()
    error_file_path = os.path.join(APP_DATA_DIR_FOR_ERROR, "shootingapp_critical_error.txt")

try:
    # --- TOÀN BỘ CODE GỐC CỦA BẠN SẼ NẰM TRONG KHỐI TRY NÀY ---
    import logging
    import json
    import shutil
    from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
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
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    logging.info("--- Application Started ---")

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
            if not ok: return False
            if verify_key(key):
                with open(license_file_path, 'w', encoding='utf-8') as f: f.write(key)
                QMessageBox.information(None, "Thành công", "Kích hoạt thành công! Ứng dụng sẽ khởi động.")
                return True
            else:
                QMessageBox.warning(None, "Lỗi", "License Key không hợp lệ cho máy tính này. Vui lòng thử lại.")

    class ApplicationController(QMainWindow):
        def __init__(self):
            super().__init__()
            self.config = self._load_config()
            self._ensure_assets_are_in_appdata()
            app_title = self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng")
            self.setWindowTitle(app_title)
            self.setStyleSheet("background-color: #2c3e50;")
            logging.info(f"Configuration loaded: {self.config}")
            self.processing_thread = QThread()
            self.processing_worker = ProcessingWorker(self.config)
            self.bt_trigger = BluetoothTrigger()
            self.processing_thread.setObjectName("ProcessingThread")
            self.processing_worker.moveToThread(self.processing_thread)
            self.main_menu = MainMenuWindow()
            self.practice_screen = PracticeWindow(worker=self.processing_worker, trigger=self.bt_trigger, config=self.config)
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
            if os.path.exists(dest_path):
                try:
                    with open(dest_path, 'r', encoding='utf-8') as f: return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logging.error(f"Lỗi khi đọc config từ AppData: {e}")
            QMessageBox.critical(None, "Lỗi nghiêm trọng", "Không thể tải file cấu hình (config.json). Ứng dụng có thể không hoạt động đúng.")
            return {}

        def _ensure_assets_are_in_appdata(self):
            # SỬA LỖI 1: Đọc đúng key "yolo_model_path" thay vì "yolo_model_name"
            model_relative_path = self.config.get("yolo_model_path") 
            
            if not model_relative_path:
                logging.error("Config thiếu key 'yolo_model_path'. Không thể tải model.")
                return
            
            # Đường dẫn đầy đủ nơi file model SẼ NẰM trong AppData
            dest_model_path = os.path.join(APP_DATA_DIR, model_relative_path) 
            
            if not os.path.exists(dest_model_path):
                logging.info(f"Model '{model_relative_path}' không tìm thấy trong AppData. Sao chép từ file mặc định.")
                
                # SỬA LỖI 2: Lấy đường dẫn nguồn của model từ resource_path
                # Đường dẫn này là đường dẫn tương đối trong gói cài đặt (ví dụ: assets/models/K54v2.pt)
                source_model_path = resource_path(model_relative_path)

                if os.path.exists(source_model_path):
                    try:
                        # SỬA LỖI 3: Đảm bảo thư mục đích tồn tại trước khi sao chép
                        # (ví dụ: tạo thư mục .../Training54/assets/models/)
                        os.makedirs(os.path.dirname(dest_model_path), exist_ok=True)
                        
                        shutil.copyfile(source_model_path, dest_model_path)
                        logging.info(f"Đã sao chép thành công model mặc định vào AppData.")
                    except (IOError, shutil.SameFileError) as e:
                        logging.error(f"Không thể sao chép file model mặc định: {e}")
                        QMessageBox.critical(None, "Lỗi Sao chép Model", f"Không thể sao chép model AI cần thiết vào thư mục dữ liệu.\nLỗi: {e}")
                else:
                    logging.error(f"Lỗi nghiêm trọng: Không tìm thấy file model gốc tại '{source_model_path}'.")
                    QMessageBox.critical(None, "Lỗi Thiếu Model", f"Không tìm thấy file model AI '{model_relative_path}' trong gói cài đặt.")
        
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
            if self.bt_trigger: self.bt_trigger.stop_global_listener()
            if self.processing_thread.isRunning():
                self.processing_thread.quit()
                if not self.processing_thread.wait(3000): self.processing_thread.terminate()
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

    # --- Phần `main` gốc ---
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

# =============================================================================
# === KẾT THÚC BẪY LỖI ===
# =============================================================================
except Exception:
    # Ghi lại toàn bộ thông tin lỗi (traceback) vào file
    with open(error_file_path, "w", encoding="utf-8") as f:
        f.write("An unexpected error occurred during application startup:\n")
        f.write(traceback.format_exc())
    
    # Hiển thị thông báo lỗi thân thiện cho người dùng
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None, 
            "Lỗi Khởi Động Nghiêm Trọng",
            f"Ứng dụng đã gặp lỗi và không thể bắt đầu.\n\n"
            f"Vui lòng gửi file sau cho nhà phát triển:\n{error_file_path}"
        )
    except Exception:
        # Fallback nếu ngay cả PySide cũng không thể import
        pass
    sys.exit(1)