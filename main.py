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

    # === SỬA LỖI CRASH THẦM LẶNG ===
    # Khởi tạo QApplication LÊN ĐẦU TIÊN, trước khi import bất cứ thứ gì.
    # Việc này đảm bảo các module (như scaler.py) có thể hoạt động.
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    # === KẾT THÚC SỬA LỖI ===

    import logging
    import json
    import shutil
    # (QApplication đã được import ở trên)
    from PySide6.QtWidgets import QMainWindow, QStackedWidget, QInputDialog, QLineEdit, QMessageBox
    from PySide6.QtCore import QThread, Slot # <-- Thêm Slot
    from PySide6.QtGui import QIcon
    from utils.resource_path import resource_path

    # === BẮT ĐẦU VÙNG SỬA ĐỔI 1: IMPORT CÁC CỬA SỔ CÒN THIẾU ===
    from gui.windows.main_menu_window import MainMenuWindow
    from gui.windows.practice_window import PracticeWindow
    from gui.windows.manage_window import ManageWindow
    # Import các cửa sổ "Kiểm tra"
    from gui.windows.competition_menu_window import CompetitionMenuWindow
    from gui.windows.setup_competition_window import SetupCompetitionWindow
    from gui.windows.saved_competitions_window import SavedCompetitionsWindow
    from gui.windows.competition_stats_window import CompetitionStatsWindow
    from gui.windows.competition_window import CompetitionWindow
    # === KẾT THÚC VÙNG SỬA ĐỔI 1 ===

    from core.worker import ProcessingWorker
    from core.triggers import BluetoothTrigger
    from config import APP_DATA_DIR
    from utils.license_manager import verify_key
    from core.database import DatabaseManager # Import DatabaseManager

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

            # === BẮT ĐẦU VÙNG SỬA ĐỔI 2: KHỞI TẠO CÁC CỬA SỔ ===
            self.db = DatabaseManager() # Khởi tạo DB
            self.processing_thread = QThread()
            self.processing_worker = ProcessingWorker(self.config)
            self.bt_trigger = BluetoothTrigger()
            self.processing_thread.setObjectName("ProcessingThread")
            self.processing_worker.moveToThread(self.processing_thread)
            
            # Khởi tạo các cửa sổ gốc
            self.main_menu = MainMenuWindow() 
            self.practice_screen = PracticeWindow(worker=self.processing_worker, trigger=self.bt_trigger, config=self.config)
            self.manage_screen = ManageWindow(self.config)
            
            # Khởi tạo các cửa sổ kiểm tra còn thiếu
            self.competition_menu = CompetitionMenuWindow()
            self.setup_competition_screen = SetupCompetitionWindow()
            self.saved_competitions_screen = SavedCompetitionsWindow()
            self.competition_stats_screen = CompetitionStatsWindow()
            self.competition_screen = CompetitionWindow(worker=self.processing_worker, trigger=self.bt_trigger, config=self.config)
            # === KẾT THÚC VÙNG SỬA ĐỔI 2 ===
            
            self.stacked_widget = QStackedWidget()
            self.setCentralWidget(self.stacked_widget)
            
            # === BẮT ĐẦU VÙNG SỬA ĐỔI 3: THÊM CỬA SỔ VÀO STACK ===
            self.stacked_widget.addWidget(self.main_menu)
            self.stacked_widget.addWidget(self.practice_screen)
            self.stacked_widget.addWidget(self.manage_screen)
            # Thêm các cửa sổ kiểm tra
            self.stacked_widget.addWidget(self.competition_menu)
            self.stacked_widget.addWidget(self.setup_competition_screen)
            self.stacked_widget.addWidget(self.saved_competitions_screen)
            self.stacked_widget.addWidget(self.competition_stats_screen)
            self.stacked_widget.addWidget(self.competition_screen)
            # === KẾT THÚC VÙNG SỬA ĐỔI 3 ===

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
            # Đã sửa (đọc yolo_model_path)
            model_relative_path = self.config.get("yolo_model_path") 
            
            if not model_relative_path:
                logging.error("Config thiếu key 'yolo_model_path'. Không thể tải model.")
                return
            
            dest_model_path = os.path.join(APP_DATA_DIR, model_relative_path) 
            
            if not os.path.exists(dest_model_path):
                logging.info(f"Model '{model_relative_path}' không tìm thấy trong AppData. Sao chép từ file mặc định.")
                
                source_model_path = resource_path(model_relative_path)

                if os.path.exists(source_model_path):
                    try:
                        os.makedirs(os.path.dirname(dest_model_path), exist_ok=True)
                        
                        shutil.copyfile(source_model_path, dest_model_path)
                        logging.info(f"Đã sao chép thành công model mặc định vào AppData.")
                    except (IOError, shutil.SameFileError) as e:
                        logging.error(f"Không thể sao chép file model mặc định: {e}")
                        QMessageBox.critical(None, "Lỗi Sao chép Model", f"Không thể sao chép model AI cần thiết vào thư mục dữ liệu.\nLỗi: {e}")
                else:
                    logging.error(f"Lỗi nghiêm trọng: Không tìm thấy file model gốc tại '{source_model_path}'.")
                    QMessageBox.critical(None, "Lỗi Thiếu Model", f"Không thể tìm thấy file model AI '{model_relative_path}' trong gói cài đặt.")
        
        # === BẮT ĐẦU VÙNG SỬA ĐỔI 4: KẾT NỐI TẤT CẢ TÍN HIỆU ===
        def connect_signals(self):
            # --- Menu chính ---
            self.main_menu.practice_button.clicked.connect(self.show_practice_screen)       
            self.main_menu.stats_button.clicked.connect(self.show_manage_screen)
            self.main_menu.exit_button.clicked.connect(self.close)
            self.main_menu.competition_button.clicked.connect(self.show_competition_menu) # <-- SỬA LỖI Ở ĐÂY

            # --- Luồng Tập luyện ---
            self.practice_screen.back_to_main_menu.connect(self.show_main_menu)
            self.practice_screen.request_processing.connect(self.processing_worker.process_image)
            self.processing_worker.practice_finished.connect(self.practice_screen.on_processing_finished)
            
            # --- Luồng Quản lý ---
            self.manage_screen.back_to_main_menu.connect(self.show_main_menu) # Sửa (từ self.manage_screen.ui.back_button)

            # --- Luồng Kiểm tra (Mới) ---
            # Từ Menu Kiểm tra -> các màn hình con
            self.competition_menu.start_button.clicked.connect(self.show_setup_competition)
            self.competition_menu.saved_button.clicked.connect(self.show_saved_competitions)
            self.competition_menu.stats_button.clicked.connect(self.show_competition_stats)
            self.competition_menu.back_button.clicked.connect(self.show_main_menu)

            # Từ Setup -> Bắt đầu thi
            self.setup_competition_screen.ui.back_button.clicked.connect(self.show_competition_menu)
            self.setup_competition_screen.start_competition_signal.connect(self.start_new_competition)

            # Từ Saved -> Tiếp tục thi
            self.saved_competitions_screen.back_to_menu_signal.connect(self.show_competition_menu)
            self.saved_competitions_screen.resume_competition_signal.connect(self.resume_competition)

            # Từ Stats -> Quay lại
            self.competition_stats_screen.back_to_menu_signal.connect(self.show_competition_menu)

            # Từ màn hình Bắn -> Quay lại
            self.competition_screen.back_to_menu_signal.connect(self.show_competition_menu_after_comp)
            
            # Kết nối worker cho màn hình kiểm tra
            self.competition_screen.request_processing.connect(self.processing_worker.process_image)
            self.processing_worker.competition_finished.connect(self.competition_screen.handle_processing_result)
            
            # --- Trigger Cò súng ---
            # Sửa lại để trigger gọi 1 hàm điều phối
            self.bt_trigger.triggered.connect(self.handle_global_trigger)
        # === KẾT THÚC VÙNG SỬA ĐỔI 4 ===

        def cleanup_before_exit(self):
            print("INFO: Bắt đầu quá trình dọn dẹp ứng dụng...")
            if self.bt_trigger: self.bt_trigger.stop_global_listener()
            if self.processing_thread.isRunning():
                self.processing_thread.quit()
                if not self.processing_thread.wait(3000): self.processing_thread.terminate()
            print("INFO: Dọn dẹp hoàn tất.")

        # === BẮT ĐẦU VÙNG SỬA ĐỔI 5: THÊM CÁC HÀM SLOT ĐỂ CHUYỂN MÀN HÌNH ===
        @Slot()
        def handle_global_trigger(self):
            """Phân phối tín hiệu cò súng đến đúng màn hình đang hoạt động."""
            current_widget = self.stacked_widget.currentWidget()
            if current_widget == self.practice_screen:
                self.practice_screen.capture_photo()
            elif current_widget == self.competition_screen:
                self.competition_screen.handle_shot()

        @Slot()
        def show_main_menu(self):
            """Hiển thị menu chính, tắt camera của các màn hình khác."""
            current_widget = self.stacked_widget.currentWidget()
            if current_widget == self.practice_screen:
                self.practice_screen.shutdown_components()
            elif current_widget == self.competition_screen:
                # Màn hình thi đấu sẽ tự xử lý tắt camera khi phát tín hiệu back_to_menu_signal
                # (thông qua `_prompt_exit` và `shutdown_components`)
                pass
            
            self.stacked_widget.setCurrentWidget(self.main_menu)

        @Slot()
        def show_practice_screen(self):
            self.practice_screen.load_soldiers() # Tải lại danh sách lính mỗi khi vào
            self.practice_screen.start_camera()
            self.stacked_widget.setCurrentWidget(self.practice_screen)
        
        @Slot()
        def show_manage_screen(self):
            self.manage_screen.load_soldiers() # Tải lại danh sách lính mỗi khi vào
            self.manage_screen.set_panels_state("NO_SOLDIER_SELECTED") # Reset UI
            self.stacked_widget.setCurrentWidget(self.manage_screen)

        @Slot()
        def show_competition_menu(self):
            """Hiển thị menu kiểm tra, tắt camera nếu đang từ màn hình bắn."""
            current_widget = self.stacked_widget.currentWidget()
            if current_widget == self.competition_screen:
                self.competition_screen.shutdown_components()
            self.stacked_widget.setCurrentWidget(self.competition_menu)

        @Slot()
        def show_competition_menu_after_comp(self):
            """
            Slot riêng được gọi bởi màn hình bắn (competition_screen)
            sau khi nó đã tự xử lý logic thoát (lưu/xóa/hủy).
            """
            self.competition_screen.shutdown_components()
            self.stacked_widget.setCurrentWidget(self.competition_menu)

        @Slot()
        def show_setup_competition(self):
            self.setup_competition_screen.load_soldiers()
            self.setup_competition_screen.reset_form() # Xóa các lựa chọn cũ
            self.stacked_widget.setCurrentWidget(self.setup_competition_screen)

        @Slot()
        def show_saved_competitions(self):
            self.saved_competitions_screen.enter_view() # Tải danh sách các cuộc thi đã lưu
            self.stacked_widget.setCurrentWidget(self.saved_competitions_screen)

        @Slot()
        def show_competition_stats(self):
            self.competition_stats_screen.enter_view() # Tải danh sách các cuộc thi đã hoàn thành
            self.stacked_widget.setCurrentWidget(self.competition_stats_screen)

        @Slot(str, list)
        def start_new_competition(self, competition_name, participant_ids):
            """Bắt đầu một cuộc thi mới từ màn hình setup."""
            # Lấy danh sách đối tượng lính đầy đủ từ ID
            all_soldiers = self.db.get_all_soldiers()
            participants = [p for p in all_soldiers if p['id'] in participant_ids]
            
            # Tạo cuộc thi trong DB
            comp_id = self.db.create_competition(competition_name, participant_ids)
            if comp_id is None:
                QMessageBox.critical(self, "Lỗi Database", f"Không thể tạo cuộc thi '{competition_name}'. Tên có thể đã tồn tại.")
                return
                
            self.competition_screen.setup_competition(comp_id, competition_name, participants)
            self.competition_screen.start_camera()
            self.stacked_widget.setCurrentWidget(self.competition_screen)

        @Slot(dict)
        def resume_competition(self, state_dict):
            """Tiếp tục một cuộc thi đã lưu từ màn hình saved."""
            self.competition_screen.load_from_state(state_dict)
            self.competition_screen.start_camera()
            self.stacked_widget.setCurrentWidget(self.competition_screen)
        # === KẾT THÚC VÙNG SỬA ĐỔI 5 ===

    # --- Phần `main` gốc ---
    
    # app = QApplication(sys.argv) # <--- ĐÃ XÓA DÒNG NÀY (ĐÃ CHUYỂN LÊN ĐẦU)
    
    icon_path = resource_path("assets/app_icon.ico")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    
    if check_or_request_license():
        controller = ApplicationController() # Bây giờ gọi Controller là an toàn
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
        # app = QApplication(sys.argv) # <--- Không cần tạo app nữa vì nó đã ở trên
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