# file: gui/windows/practice_window.py
import logging
import cv2
import numpy as np
from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import QTimer, Signal, QThread, Slot
from PySide6.QtGui import QGuiApplication

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager
from ..statistics_window import StatisticsWindow

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Màn Hình Tập Luyện")
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.setGeometry(screen)
        
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        
        self.cam = None
        self.calibrated_center = None
        self.video_timer = QTimer(self)
        
        self.audio_manager = AudioManager()
        self.db_manager = DatabaseManager()
        self.active_user = None
        self.active_session_id = None
        self.is_session_active = False
        
        self.worker_thread = QThread()
        self.worker = ProcessingWorker()
        self.worker.moveToThread(self.worker_thread)
        self.setup_worker_connections()
        self.worker_thread.start()
        
        self.trigger = BluetoothTrigger()
        self.trigger.triggered.connect(self.capture_and_process)
        self.trigger.start_listening()
        
        self.setup_gui_connections()
        self._populate_users()

    def start_camera(self):
        logger.info("Practice screen is now visible. Starting camera...")
        self._populate_users() # Cập nhật danh sách người dùng mỗi khi vào màn hình
        if not self.video_timer.isActive():
            self.refresh_camera_connection()

    def setup_gui_connections(self):
        self.gui.zoom_slider.valueChanged.connect(self.handle_zoom_change)
        self.gui.calibrate_button.clicked.connect(self.calibrate_center)
        self.gui.stats_button.clicked.connect(self.show_statistics_window)
        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.user_selector.currentIndexChanged.connect(self._on_user_selected)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.camera_view_label.clicked.connect(self.handle_camera_view_click)
        self.video_timer.timeout.connect(self.update_frame)

    def setup_worker_connections(self):
        # Tên signal và slot trong worker của bạn có thể khác
        # Hãy đảm bảo chúng khớp, ví dụ: process_image hoặc process_photo
        self.request_processing.connect(self.worker.process_image) 
        self.worker.finished.connect(self.handle_processing_done)

    def _populate_users(self):
        try:
            current_selection = self.gui.user_selector.currentData()
            self.gui.user_selector.clear()
            users = self.db_manager.get_all_users()
            if users:
                for user in users:
                    self.gui.user_selector.addItem(user['name'], userData=user)
                
                # Cố gắng khôi phục lựa chọn trước đó
                if current_selection:
                    index = self.gui.user_selector.findData(current_selection)
                    if index != -1:
                        self.gui.user_selector.setCurrentIndex(index)
            else:
                self.gui.user_selector.addItem("Chưa có người dùng")
        except Exception as e:
            logger.error(f"Lỗi khi tải danh sách người dùng: {e}")

    @Slot(int)
    def _on_user_selected(self, index):
        user_data = self.gui.user_selector.itemData(index)
        if user_data:
            if self.is_session_active:
                QMessageBox.warning(self, "Phiên đang hoạt động", "Vui lòng kết thúc phiên hiện tại trước khi đổi người bắn.")
                previous_index = self.gui.user_selector.findData(self.active_user)
                if previous_index != -1:
                    self.gui.user_selector.setCurrentIndex(previous_index)
                return
            self.active_user = user_data
            logger.info(f"Đã chọn người dùng: {self.active_user['name']}")
        else:
            self.active_user = None

    def update_frame(self):
        if self.cam:
            ret, frame = self.cam.read()
            if ret:
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
        if not self.is_session_active:
            QMessageBox.information(self, "Thông báo", "Vui lòng bắt đầu phiên bắn trước.")
            return
        if self.active_user is None:
            QMessageBox.warning(self, "Chưa chọn người bắn", "Vui lòng chọn người bắn từ danh sách.")
            return

        frame = self.gui.current_frame 
        if frame is not None:
            self.audio_manager.play_shot_sound()
            # Logic get_selected_target_type cần được thêm vào ui_practice.py nếu chưa có
            target_type = "bia_so_4" # Tạm thời hardcode, bạn nên có combobox chọn bia
            self.request_processing.emit(frame, self.calibrated_center, target_type)
            logger.info("Đã chụp ảnh và gửi yêu cầu xử lý.")
        else:
            logger.warning("Không thể chụp ảnh: Camera chưa kết nối.")

    @Slot(dict)
    def handle_processing_done(self, result):
        shot_id = self.db_manager.insert_shot_data(
            session_id=self.active_session_id,
            score=result.get('score'),
            hit_x=result.get('coords', (None, None))[0],
            hit_y=result.get('coords', (None, None))[1],
            target_type=result.get('target_name'),
            image_path=result.get('image_path')
        )
        logger.info(f"Đã lưu kết quả bắn với ID: {shot_id}")
        self.gui.update_results(**result)

    @Slot(int)
    def handle_zoom_change(self, value):
        zoom_factor = value / 10.0
        self.gui.zoom_value_label.setText(f"{zoom_factor:.1f}x")
        # Logic zoom hình ảnh cần được xử lý trong VideoLabel

    def calibrate_center(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")
        if not is_calibrating:
            self.calibrated_center = None

    def handle_camera_view_click(self, position):
        if self.gui.camera_view_label._is_calibrating:
            self.calibrated_center = (position.x(), position.y())
            logger.info(f"Tâm ngắm đã được hiệu chỉnh tại: {self.calibrated_center}")
            self.gui.camera_view_label.set_calibration_mode(False)
            self.gui.calibrate_button.setText("Hiệu chỉnh tâm")

    def toggle_session(self):
        if self.is_session_active:
            # Kết thúc phiên
            self.is_session_active = False
            self.active_session_id = None
            self.gui.session_button.setText("Bắt đầu")
            self.gui.user_selector.setEnabled(True)
            logger.info("Đã kết thúc phiên bắn.")
        else:
            # Bắt đầu phiên mới
            if self.active_user is None:
                QMessageBox.warning(self, "Chưa chọn người bắn", "Vui lòng chọn người bắn trước khi bắt đầu.")
                return
            self.active_session_id = self.db_manager.create_shot_session(self.active_user['id'])
            self.is_session_active = True
            self.gui.session_button.setText("Kết thúc")
            self.gui.user_selector.setEnabled(False) # Không cho đổi người khi đang bắn
            logger.info(f"Bắt đầu phiên bắn mới cho '{self.active_user['name']}' với session ID: {self.active_session_id}")

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
            logger.info(f"Đã kết nối camera tại chỉ số {index}.")
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
        if all_cameras:
            target_index = 0 # Luôn chọn camera đầu tiên
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera tại chỉ số {target_index}.")
            self.connect_camera(target_index)
        else:
            logger.warning("Không tìm thấy camera nào.")
            self.disconnect_camera("Không tìm thấy camera")