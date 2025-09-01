# main_window.py
import logging
import cv2
import numpy as np
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer, QObject, Signal, QPoint, QThread, Slot
from PySide6.QtGui import QScreen
from datetime import datetime

# THAY ĐỔI: Import từ các file mới
from gui.gui import MainGui
from utils.audio import AudioManager
from utils.camera import Camera, find_available_cameras
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    # Tín hiệu để gửi việc cho Worker
    request_processing = Signal(np.ndarray, object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)

        # --- Thuộc tính Giao diện & Camera ---
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        
        # --- Các Module phụ trợ ---
        self.audio_manager = AudioManager()
        self.video_timer = QTimer(self)
        self.bt_trigger = BluetoothTrigger()

        # --- Thiết lập Worker bền bỉ ---
        self.processing_thread = QThread()
        self.worker = ProcessingWorker()
        self.worker.moveToThread(self.processing_thread)

        # --- Kết nối Tín hiệu (Signals) & Tác vụ (Slots) ---
        self.request_processing.connect(self.worker.process_image)
        self.worker.finished.connect(self.on_processing_finished)
        self.processing_thread.finished.connect(self.worker.deleteLater)
        self.video_timer.timeout.connect(self.update_frame)
        self.bt_trigger.triggered.connect(self.capture_photo)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        
        # --- Khởi động ---
        self.processing_thread.start()
        self.bt_trigger.start_listening()
        self.refresh_camera_connection()

    def update_frame(self):
        if not (self.cam and self.cam.is_opened()): return
        frame = self.cam.grab()
        if frame is None:
            self.disconnect_camera()
            return
        
        processed_frame = self.crop_and_resize_frame(frame)
        self.gui.current_frame = processed_frame.copy()
        zoomed_frame = self.apply_digital_zoom(processed_frame, self.zoom_level)
        
        center_point = self.calibrated_center or (zoomed_frame.shape[1] // 2, zoomed_frame.shape[0] // 2)
        cv2.drawMarker(zoomed_frame, center_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
        self.gui.display_frame(zoomed_frame)
    
    def capture_photo(self):
        """Gửi tín hiệu yêu cầu xử lý, không trực tiếp quản lý luồng."""
        if self.gui.current_frame is not None:
            self.audio_manager.play_sound('shot')
            # Chỉ cần phát tín hiệu mang theo dữ liệu cần xử lý
            self.request_processing.emit(self.gui.current_frame, self.calibrated_center)
            logger.info("GUI: Đã gửi yêu cầu xử lý cho worker.")
        else:
            logger.warning("Không có frame nào để chụp.")
            
    @Slot(dict)
    
    def on_processing_finished(self, result):
        """Nhận kết quả từ luồng nền và cập nhật lên giao diện."""
        logger.info("GUI: Nhận được kết quả, đang cập nhật giao diện...")
        zoomed_photo = self.apply_digital_zoom(result['result_frame'], self.zoom_level)
        self.gui.update_results(
            time_str=result['time_str'],
            target_name=result['target_name'],
            score=result['score'],
            result_frame=zoomed_photo
        )

    def closeEvent(self, event):
        """Dọn dẹp tài nguyên trước khi đóng ứng dụng."""
        self.video_timer.stop()
        self.bt_trigger.stop_listening()
        self.disconnect_camera()
        
        # Yêu cầu luồng nền dừng lại và chờ nó kết thúc
        self.processing_thread.quit()
        self.processing_thread.wait(3000)
        super().closeEvent(event)

    # --- Các hàm còn lại không thay đổi đáng kể ---
    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape
        target_aspect_ratio = 3.0 / 4.0
        new_w = int(h * target_aspect_ratio)
        start_x = (w - new_w) // 2 if w > new_w else 0
        cropped_frame = frame[:, start_x : start_x + new_w]
        return cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)

    def apply_digital_zoom(self, frame, zoom):
        if zoom <= 1.0: return frame
        h, w, _ = frame.shape
        crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")

    def set_new_center(self, click_pos: QPoint):
        widget_size = self.gui.camera_view_label.size()
        img_w, img_h = self.final_size
        scale = min(widget_size.width() / img_w, widget_size.height() / img_h)
        display_w, display_h = int(img_w * scale), int(img_h * scale)
        offset_x, offset_y = (widget_size.width() - display_w) // 2, (widget_size.height() - display_h) // 2
        if offset_x <= click_pos.x() < offset_x + display_w and offset_y <= click_pos.y() < offset_y + display_h:
            img_x = int((click_pos.x() - offset_x) / scale)
            img_y = int((click_pos.y() - offset_y) / scale)
            self.calibrated_center = (img_x, img_y)
            self.toggle_calibration_mode()

    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0
    
    def connect_camera(self, index):
        self.disconnect_camera()
        self.cam = Camera(index)
        if self.cam.is_opened() and self.cam.grab() is not None:
            self.video_timer.start(30)
        else:
            self.disconnect_camera()

    def disconnect_camera(self):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None
        self.gui.clear_video_feed("Vui lòng kết nối camera")
    
    def refresh_camera_connection(self):
        all_cameras = find_available_cameras()
        if all_cameras:
            self.connect_camera(all_cameras[0])
        else:
            self.disconnect_camera()