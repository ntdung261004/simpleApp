# file: gui/windows/practice_window.py
import logging
import time
import os
from datetime import datetime
import numpy as np
import cv2

from PySide6.QtWidgets import QMainWindow, QMessageBox
from PySide6.QtCore import QTimer, Signal, QThread, Slot, QPoint

# Sửa lại các đường dẫn import cho đúng cấu trúc
from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self):
        super().__init__()
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        
        # --- KHAI BÁO BIẾN, KHÔNG KHỞI TẠO ---
        self.cam = None
        self.video_timer = QTimer(self)
        self.db_manager = DatabaseManager()
        
        self.audio_manager = None
        self.bt_trigger = None
        self.worker = None
        self.processing_thread = None
        
        self.active_session_id = None
        self.save_dir = "captured_images"
        self.is_initialized = False # Cờ để chỉ khởi tạo 1 lần
        
        self.final_size = (640, 480) # Kích thước tiêu chuẩn
        self.zoom_level = 1.0
        self.calibrated_center = None

        self.setup_gui_connections()
        
    def initialize_components(self):
        """Khởi tạo các thành phần nặng chỉ khi cần thiết."""
        if self.is_initialized:
            return
            
        logger.info("PRACTICE: Bắt đầu khởi tạo các thành phần nặng (Worker, Audio, Trigger)...")
        
        self.audio_manager = AudioManager()
        self.bt_trigger = BluetoothTrigger()
        self.worker = ProcessingWorker()
        self.processing_thread = QThread()
        self.worker.moveToThread(self.processing_thread)

        self.request_processing.connect(self.worker.process_image)
        self.worker.finished.connect(self.on_processing_finished)
        self.bt_trigger.triggered.connect(self.capture_photo)
        
        self.processing_thread.start()
        self.bt_trigger.start_listening()
        
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
        
        self.is_initialized = True
        logger.info("PRACTICE: Đã khởi tạo xong các thành phần.")
        
    def start_practice(self):
        """Được gọi từ main.py để bắt đầu màn hình luyện tập."""
        logger.info("PRACTICE: Màn hình được kích hoạt.")
        self.initialize_components()
        self.populate_soldier_selector()
        
        if self.cam is None or not self.cam.isOpened():
            self.refresh_camera_connection()
            
    def shutdown_components(self):
        """Dọn dẹp tài nguyên khi quay về menu."""
        logger.info("PRACTICE: Dọn dẹp tài nguyên...")
        self.disconnect_camera()
        
        if self.bt_trigger: self.bt_trigger.stop_listening()
        if self.processing_thread:
            self.processing_thread.quit()
            self.processing_thread.wait(2000)

    def setup_gui_connections(self):
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)

    def closeEvent(self, event):
        self.shutdown_components()
        self.db_manager.close()
        event.accept()

    def refresh_camera_connection(self):
        logger.info("PRACTICE: Bắt đầu làm mới kết nối camera...")
        all_cameras = find_available_cameras()
        
        if len(all_cameras) > 1:
            target_index = 0
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera USB tại index {target_index}.")
            self.connect_camera(target_index)
        elif len(all_cameras) == 1:
            logger.warning("Chỉ phát hiện 1 camera (laptop). Yêu cầu kết nối camera USB.")
            self.disconnect_camera(message="Vui lòng cắm USB Camera và nhấn Làm mới")
        else:
            logger.warning("Không tìm thấy camera nào.")
            self.disconnect_camera(message="Không tìm thấy camera")

    def connect_camera(self, index):
        self.disconnect_camera()
        self.cam = Camera(index)
        
        if not self.cam.isOpened():
            self.disconnect_camera(f"Lỗi: Không thể mở Camera {index}")
            return

        is_frame_read = False
        for _ in range(10): # Thử lại 10 lần
            ret, frame = self.cam.read()
            if ret and frame is not None:
                is_frame_read = True
                break
            time.sleep(0.1)
        
        if is_frame_read:
            self.video_timer.start(30)
            logger.info(f"PRACTICE: Kết nối và xác thực thành công camera index {index}.")
        else:
            logger.error(f"PRACTICE: Kết nối thất bại, không đọc được frame từ camera index {index} sau 10 lần thử.")
            self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")

    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None
        self.gui.clear_video_feed(message)
    
    def update_frame(self):
        if not (self.cam and self.cam.isOpened()): return
        
        ret, frame = self.cam.read()
        if not ret or frame is None: return

        processed_frame = self.crop_and_resize_frame(frame)
        self.gui.current_frame = processed_frame.copy()
        zoomed_frame = self.apply_digital_zoom(processed_frame, self.zoom_level)
        
        point_to_draw = None
        if self.calibrated_center:
            cx, cy = self.calibrated_center
            h, w, _ = processed_frame.shape
            start_x = (w - int(w / self.zoom_level)) // 2
            start_y = (h - int(h / self.zoom_level)) // 2
            if cx >= start_x and cy >= start_y:
                zoomed_cx = int((cx - start_x) * self.zoom_level)
                zoomed_cy = int((cy - start_y) * self.zoom_level)
                if zoomed_cx < w and zoomed_cy < h:
                    point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            h_zoom, w_zoom, _ = zoomed_frame.shape
            point_to_draw = (w_zoom // 2, h_zoom // 2)

        if point_to_draw:
            cv2.drawMarker(zoomed_frame, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)

        self.gui.display_frame(zoomed_frame)
    
    def capture_photo(self):
        if not (self.cam and self.cam.isOpened()):
            logger.warning("Camera chưa kết nối, không thể chụp ảnh.")
            return

        ret, raw_frame = self.cam.read()
        if not ret or raw_frame is None:
            logger.error("Không thể lấy frame từ camera khi chụp.")
            return
            
        processed_frame = self.crop_and_resize_frame(raw_frame)
        self.audio_manager.play_sound('shot')
        
        try:
            image_to_save = self.apply_digital_zoom(processed_frame, self.zoom_level)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"shot_{timestamp}.png"
            save_path = os.path.join(self.save_dir, filename)
            cv2.imwrite(save_path, image_to_save)
            
            self.request_processing.emit(processed_frame, self.calibrated_center, save_path)
            logger.info("GUI: Đã gửi yêu cầu xử lý cho worker.")
        except Exception as e:
            logger.error(f"Lỗi khi đang lưu ảnh: {e}")

    @Slot(dict)
    def on_processing_finished(self, result):
        logger.info("GUI: Nhận được kết quả, đang cập nhật giao diện...")
        if self.active_session_id:
            self.db_manager.add_shot(
                session_id=self.active_session_id,
                score=result.get('score'),
                target_detected=result.get('target_name'), # Sửa tên cột cho khớp DB
                coords=result.get('coords'),
                image_path=result.get('image_path')
            )

        score = result.get('score')
        if score is not None and score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')

        self.gui.update_results(
            time_str=result.get('time_str'),
            target_name=result.get('target_name'),
            score=score,
            result_frame=result.get('result_frame')
        )
        
    def populate_soldier_selector(self):
        self.gui.soldier_selector.clear()
        soldiers = self.db_manager.get_all_soldiers()
        if soldiers:
            for s in soldiers: self.gui.soldier_selector.addItem(s['name'], userData=s)
        else:
            self.gui.soldier_selector.addItem("Chưa có người bắn")

    def toggle_session(self):
        if self.active_session_id is None:
            selected_index = self.gui.soldier_selector.currentIndex()
            if selected_index < 0 or self.gui.soldier_selector.itemData(selected_index) is None:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một người bắn.")
                return
            soldier_data = self.gui.soldier_selector.itemData(selected_index)
            session_id = self.db_manager.create_session(soldier_id=soldier_data['id'])
            if session_id:
                self.active_session_id = session_id
                self.gui.session_button.setText("Kết thúc")
                self.gui.soldier_selector.setEnabled(False)
        else:
            # self.db_manager.end_session(self.active_session_id) # Cần hàm này trong DB Manager
            self.active_session_id = None
            self.gui.session_button.setText("Bắt đầu")
            self.gui.soldier_selector.setEnabled(True)

    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape
        target_aspect_ratio = 4.0 / 3.0
        current_aspect_ratio = w / h
        if current_aspect_ratio > target_aspect_ratio:
            new_w = int(h * target_aspect_ratio)
            start_x = (w - new_w) // 2
            cropped = frame[:, start_x:start_x + new_w]
        else:
            new_h = int(w / target_aspect_ratio)
            start_y = (h - new_h) // 2
            cropped = frame[start_y:start_y + new_h, :]
        return cv2.resize(cropped, self.final_size, interpolation=cv2.INTER_AREA)

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
        # ... logic này khá phức tạp, giữ nguyên logic cũ của bạn ...
        pass

    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0