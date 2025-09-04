# file: gui/windows/practice_window.py
import os
import logging
import cv2
import numpy as np
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import QTimer, Signal, QThread, Slot
from PySide6.QtGui import QScreen, QGuiApplication
from datetime import datetime

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager
from ..user_dialog import UserDialog
from ..statistics_window import StatisticsWindow

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        self.cam = None
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.video_timer = QTimer(self)
        
        self.audio_manager = AudioManager()
        self.db_manager = DatabaseManager()
        self.active_user = None
        self.active_session_id = None
        
        self.worker_thread = QThread()
        self.worker = ProcessingWorker()
        self.worker.moveToThread(self.worker_thread)
        self.setup_worker_connections()
        self.worker_thread.start()
        
        self.trigger = BluetoothTrigger()
        self.trigger.triggered.connect(self.capture_and_process)
        self.trigger.start_listening()
        
        self.setup_gui_connections()
        
    def start_camera(self):
        logger.info("Practice screen is now visible. Starting camera...")
        if not self.video_timer.isActive():
            self.refresh_camera_connection()

    def setup_gui_connections(self):
        # --- THAY ĐỔI: Sử dụng thanh trượt zoom ---
        # Kết nối tín hiệu valueChanged của thanh trượt đến hàm xử lý mới
        self.gui.zoom_slider.valueChanged.connect(self.handle_zoom_change)
        # ----------------------------------------
        
        self.gui.calibrateButton.clicked.connect(self.calibrate_center)
        self.gui.manage_users_button.clicked.connect(self.show_user_dialog)
        self.gui.stats_button.clicked.connect(self.show_statistics_window)
        self.video_timer.timeout.connect(self.update_frame)

    def setup_worker_connections(self):
        self.request_processing.connect(self.worker.process_image)
        self.worker.finished.connect(self.handle_processing_done)

    def update_frame(self):
        if self.cam:
            ret, frame = self.cam.read()
            if ret:
                # Giao việc hiển thị frame cho lớp GUI
                self.gui.display_frame(frame)
            else:
                self.disconnect_camera("Mất kết nối với camera.")

    def closeEvent(self, event):
        self.trigger.stop_listening()
        self.disconnect_camera()
        self.worker_thread.quit()
        self.worker_thread.wait()
        event.accept()

    @Slot()
    def capture_and_process(self):
        if self.active_user is None:
            QMessageBox.warning(self, "Chưa chọn người bắn", "Vui lòng chọn người bắn trước khi thực hiện.")
            return

        if self.cam and self.cam.isOpened():
            # Lấy frame hiện tại từ GUI thay vì đọc lại từ camera để đảm bảo đồng bộ
            frame = self.gui.current_frame 
            if frame is not None:
                self.audio_manager.play_shot_sound()
                self.request_processing.emit(frame, self.calibrated_center, self.gui.get_selected_target_type())
                logger.info("Đã chụp ảnh và gửi yêu cầu xử lý.")
        else:
            logger.warning("Không thể chụp ảnh: Camera chưa kết nối.")
            QMessageBox.warning(self, "Lỗi Camera", "Camera chưa được kết nối. Vui lòng kiểm tra lại.")

    @Slot(dict)
    def handle_processing_done(self, result):
        if not self.active_session_id:
            self.active_session_id = self.db_manager.create_shot_session(self.active_user['id'])
        
        shot_id = self.db_manager.insert_shot_data(
            session_id=self.active_session_id,
            score=result.get('score'),
            hit_x=result.get('coords', (None, None))[0],
            hit_y=result.get('coords', (None, None))[1],
            target_type=result.get('target_name'),
            image_path=result.get('image_path')
        )
        logger.info(f"Đã lưu kết quả bắn với ID: {shot_id}")
        
        self.gui.update_results(
            time_str=result.get('time_str'),
            target_name=result.get('target_name'),
            score=result.get('score'),
            result_frame=result.get('result_frame')
        )

    # --- THAY ĐỔI: Hàm xử lý mới cho thanh trượt ---
    @Slot(int)
    def handle_zoom_change(self, value):
        """
        Xử lý sự kiện khi giá trị của thanh trượt thay đổi.
        'value' là một số nguyên từ 0 đến 99 (mặc định của QSlider).
        Chúng ta sẽ chuyển nó thành mức zoom từ 1.0 đến 3.0.
        """
        # Công thức chuyển đổi: zoom = min_zoom + (value / max_slider_value) * (max_zoom - min_zoom)
        self.zoom_level = 1.0 + (value / 99.0) * 2.0 
        self.gui.set_zoom(self.zoom_level)
    # ----------------------------------------------
    
    # --- XÓA: Các hàm zoom_in, zoom_out không còn cần thiết ---
    # def zoom_in(self): ...
    # def zoom_out(self): ...
    # --------------------------------------------------------

    def calibrate_center(self):
        if self.calibrated_center:
            self.calibrated_center = None
            self.gui.calibrateButton.setText("Hiệu chỉnh tâm")
            self.gui.set_crosshair(None)
        else:
            frame_center_x = self.gui.camera_view_label.width() // 2
            frame_center_y = self.gui.camera_view_label.height() // 2
            self.calibrated_center = (frame_center_x, frame_center_y)
            self.gui.calibrateButton.setText("Xóa hiệu chỉnh")
            self.gui.set_crosshair(self.calibrated_center)
            
    def show_user_dialog(self):
        dialog = UserDialog(self.db_manager, self)
        if dialog.exec():
            self.active_user = dialog.get_selected_user()
            if self.active_user:
                self.gui.update_user_info(self.active_user['name'])
                self.active_session_id = None
            else:
                self.gui.update_user_info("Chưa chọn")
    
    def show_statistics_window(self):
        if self.active_user:
            stats_window = StatisticsWindow(self.db_manager, self.active_user['id'], self)
            stats_window.show()
        else:
            QMessageBox.warning(self, "Chưa chọn người bắn", "Vui lòng chọn người bắn để xem thống kê.")

    def connect_camera(self, index):
        self.disconnect_camera()
        self.cam = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if self.cam and self.cam.isOpened():
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.video_timer.start(30)
            logger.info(f"Đã kết nối thành công với camera tại chỉ số {index}.")
        else:
            self.disconnect_camera("Không thể kết nối camera.")

    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam:
            self.cam.release()
        self.cam = None
        self.gui.clear_video_feed(message)
    
    def refresh_camera_connection(self):
        logger.info("Đang tìm kiếm camera...")
        all_cameras = find_available_cameras()
        
        if len(all_cameras) > 1:
            target_index = 0
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera USB tại chỉ số {target_index}.")
            self.connect_camera(target_index)
        elif len(all_cameras) == 1:
            logger.warning("Chỉ phát hiện camera laptop. Vui lòng kết nối camera USB.")
            self.disconnect_camera(message="Vui lòng kết nối USB Camera")
        else:
            logger.warning("Không tìm thấy camera nào.")
            self.disconnect_camera(message="Không tìm thấy camera")