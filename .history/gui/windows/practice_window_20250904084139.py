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
    # Tín hiệu để gửi việc cho Worker, khớp với tham số của process_photo
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        
        # --- Thuộc tính Giao diện & Camera --
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        self.cam = None
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.video_timer = QTimer(self)
        
        # --- Các Module phụ trợ ---
        self.audio_manager = AudioManager()
        self.db_manager = DatabaseManager()
        self.active_user = None
        self.active_session_id = None
        
        # --- Worker Thread để xử lý ảnh ---
        self.worker_thread = QThread()
        self.worker = ProcessingWorker()
        self.worker.moveToThread(self.worker_thread)
        self.setup_worker_connections()
        self.worker_thread.start()
        
        # --- Trigger ---
        self.trigger = BluetoothTrigger()
        self.trigger.shot_detected.connect(self.capture_and_process)
        self.trigger.start_listening()
        
        self.setup_gui_connections()
        
    def start_camera(self):
        logger.info("Practice screen is now visible. Starting camera...")
        if not self.video_timer.isActive():
            self.refresh_camera_connection()

    def setup_gui_connections(self):
        self.gui.zoom_in_button.clicked.connect(self.zoom_in)
        self.gui.zoom_out_button.clicked.connect(self.zoom_out)
        self.gui.calibrate_button.clicked.connect(self.calibrate_center)
        self.gui.user_button.clicked.connect(self.show_user_dialog)
        self.gui.stats_button.clicked.connect(self.show_statistics_window)
        self.video_timer.timeout.connect(self.update_frame)

    def setup_worker_connections(self):
        # Kết nối tín hiệu từ main thread đến slot `process_image` của worker
        self.request_processing.connect(self.worker.process_image)
        
        # Kết nối tín hiệu `finished` từ worker về hàm xử lý kết quả
        self.worker.finished.connect(self.handle_processing_done)
        
        # Không còn các tín hiệu target_detected, target_not_detected, processing_error
        # Nếu cần xử lý lỗi, bạn có thể thêm một tín hiệu lỗi riêng trong worker.py

    def update_frame(self):
        """Cập nhật khung hình từ camera lên giao diện."""
        if self.cam:
            ret, frame = self.cam.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.gui.update_video_feed(frame_rgb, self.zoom_level, self.calibrated_center)
                # ĐÃ XÓA: Lệnh emit xử lý liên tục đã được loại bỏ.
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
            ret, frame = self.cam.read()
            if ret:
                self.audio_manager.play_shot_sound()
                # Chỉ gửi yêu cầu xử lý khi có phát bắn
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
        self.gui.update_shot_result(result)

    def zoom_in(self):
        self.zoom_level = min(3.0, self.zoom_level + 0.1)

    def zoom_out(self):
        self.zoom_level = max(1.0, self.zoom_level - 0.1)

    def calibrate_center(self):
        if self.calibrated_center:
            self.calibrated_center = None
            self.gui.calibrate_button.setText("Hiệu chỉnh tâm")
        else:
            frame_center_x = self.gui.video_label.width() // 2
            frame_center_y = self.gui.video_label.height() // 2
            self.calibrated_center = (frame_center_x, frame_center_y)
            self.gui.calibrate_button.setText("Xóa hiệu chỉnh")
            
    def show_user_dialog(self):
        dialog = UserDialog(self.db_manager, self)
        if dialog.exec():
            self.active_user = dialog.get_selected_user()
            if self.active_user:
                self.gui.update_user_info(self.active_user['name'])
                self.active_session_id = None # Reset session khi đổi user
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