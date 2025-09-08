# Thay thế TOÀN BỘ file main.py

import sys
import logging
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtCore import QThread

# Import các lớp cửa sổ và các thành phần chạy ngầm
from gui.windows.main_menu_window import MainMenuWindow
from gui.windows.practice_window import PracticeWindow
from gui.windows.manage_window import ManageWindow
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger

# Cấu hình logging cơ bản
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] (%(name)s) - %(message)s')

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
    app = QApplication(sys.argv)
    controller = ApplicationController()
    
    # Kết nối tín hiệu aboutToQuit với hàm dọn dẹp
    app.aboutToQuit.connect(controller.cleanup_before_exit)

    controller.showFullScreen()
    sys.exit(app.exec())