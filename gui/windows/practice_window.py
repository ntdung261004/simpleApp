# file: gui/windows/practice_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QApplication, QInputDialog, QLineEdit, QMessageBox
from PySide6.QtCore import QTimer, Signal, Slot, QPoint, Qt
import cv2
import numpy as np
import json
import os
from datetime import datetime
from PySide6.QtGui import QScreen

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import count_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager
from utils.filter import apply_gamma_correction
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_main_menu = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger, config: dict):
        super().__init__()
        self.setWindowTitle("Phần Mềm Luyện Tập Đường Ngắm")
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)
        self.configured_camera_index = config.get('camera_index', 0)
        self.db = DatabaseManager(); self.audio_manager = AudioManager()
        self.trigger = trigger; self.worker = worker
        self.gui = MainGui(); self.setCentralWidget(self.gui)
        self.active_session_id = None; self.cam = None; self.is_camera_connected = False
        self.final_size = (640, 480); self.zoom_level = 1.0; self.current_gamma = 1.0
        self.calibrated_center = None
        self.video_timer = QTimer(self); self.video_timer.timeout.connect(self.update_frame)
        self.setup_connections(); self.load_soldiers(); self.set_ui_state('INITIAL')

    def _crop_frame_to_3_4(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]; target_aspect = 3.0 / 4.0
        new_w = int(h * target_aspect)
        if new_w > w: return frame 
        start_x = (w - new_w) // 2
        return frame[:, start_x : start_x + new_w]

    def _apply_effects_to_frame(self, frame: np.ndarray) -> np.ndarray:
        processed_frame = frame.copy()
        if self.current_gamma != 1.0: processed_frame = apply_gamma_correction(processed_frame, self.current_gamma)
        if self.zoom_level > 1.0:
            h, w, _ = processed_frame.shape; new_w, new_h = int(w / self.zoom_level), int(h / self.zoom_level)
            start_x, start_y = (w - new_w) // 2, (h - new_h) // 2
            processed_frame = processed_frame[start_y : start_y + new_h, start_x : start_x + new_w]
            processed_frame = cv2.resize(processed_frame, (w, h))
        return processed_frame

    # === BẮT ĐẦU VÙNG SỬA LỖI ===
    @Slot()
    def capture_photo(self):
        if not self.is_camera_connected: return
        ret, frame = self.cam.read()
        if ret and frame is not None:
            self.audio_manager.play_sound('shot')
            frame_cropped = self._crop_frame_to_3_4(frame)
            frame_resized = cv2.resize(frame_cropped, (self.final_size[1], self.final_size[0]))
            
            # Sửa lại tên hàm bị sai
            frame_to_send = self._apply_effects_to_frame(frame_resized)
            
            h, w, _ = frame_resized.shape # Lấy tọa độ trên ảnh chưa zoom
            aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
            
            image_dir = os.path.join(APP_DATA_DIR, 'history_images'); os.makedirs(image_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f"); image_path = os.path.join(image_dir, f"shot_{timestamp}.jpg")
            metadata = {'aim_point': aim_point}
            
            self.request_processing.emit(frame_to_send, image_path, 'practice', metadata)
    # === KẾT THÚC VÙNG SỬA LỖI ===

    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: return
        ret, frame = self.cam.read()
        if not ret or frame is None: self.disconnect_camera("Mất kết nối camera."); return
        
        frame_cropped = self._crop_frame_to_3_4(frame)
        frame_resized = cv2.resize(frame_cropped, (self.final_size[1], self.final_size[0]))
        
        frame_with_gamma = frame_resized.copy()
        if self.current_gamma != 1.0:
            frame_with_gamma = apply_gamma_correction(frame_with_gamma, self.current_gamma)

        h, w, _ = frame_with_gamma.shape
        original_aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        
        if self.zoom_level > 1.0:
            zoomed_w, zoomed_h = int(w / self.zoom_level), int(h / self.zoom_level)
            crop_start_x, crop_start_y = (w - zoomed_w) // 2, (h - zoomed_h) // 2
            transformed_x = original_aim_point[0] - crop_start_x
            transformed_y = original_aim_point[1] - crop_start_y
            display_aim_point = (int(transformed_x * self.zoom_level), int(transformed_y * self.zoom_level))
            frame_to_display = frame_with_gamma[crop_start_y : crop_start_y + zoomed_h, crop_start_x : crop_start_x + zoomed_w]
            frame_to_display = cv2.resize(frame_to_display, (w, h))
        else:
            frame_to_display = frame_with_gamma
            display_aim_point = original_aim_point

        cv2.drawMarker(frame_to_display, display_aim_point, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        self.gui.display_frame(frame_to_display)
        
    # --- Các hàm logic còn lại không thay đổi ---
    def setup_connections(self):
        self.gui.soldier_selector.currentIndexChanged.connect(self.on_soldier_selected)
        self.gui.session_button.clicked.connect(self.toggle_session_state)
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.back_button.clicked.connect(self.back_to_main_menu.emit)
        self.back_to_main_menu.connect(self.shutdown_components)
    @Slot(dict)
    def on_processing_finished(self, result: dict):
        result_image = result.get('result_frame'); score = result.get('score', 0)
        if score == 0:
            aim_point_used = result.get('aim_point_used')
            if result_image is not None and aim_point_used is not None:
                h, w, _ = result_image.shape; original_aim_point = aim_point_used
                if self.zoom_level > 1.0:
                    zoomed_w, zoomed_h = int(w / self.zoom_level), int(h / self.zoom_level)
                    crop_start_x, crop_start_y = (w - zoomed_w) // 2, (h - zoomed_h) // 2
                    transformed_x = original_aim_point[0] - crop_start_x; transformed_y = original_aim_point[1] - crop_start_y
                    display_aim_point = (int(transformed_x * self.zoom_level), int(transformed_y * self.zoom_level))
                else: display_aim_point = original_aim_point
                cv2.drawMarker(result_image, display_aim_point, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        image_path = result.get('image_path')
        if image_path and result_image is not None:
            try: cv2.imwrite(image_path, result_image)
            except Exception as e: logger.error(f"Lỗi khi ghi đè ảnh kết quả: {e}")
        self.gui.update_results(time_str=result.get('time_str'), target_name=result.get('target_name'), score=score, result_frame=result_image)
        if score == 0: self.audio_manager.play_sound('miss')
        else: self.audio_manager.play_score(score)
        if self.active_session_id:
            shot_number = self.db.get_shot_count_for_session(self.active_session_id) + 1
            self.db.add_shot(session_id=self.active_session_id, shot_number=shot_number, score=score, target_detected=result.get('target_detected_raw', 'N/A'), coords=result.get('coords'), image_path=image_path)
    def set_ui_state(self, state: str):
        self.trigger.deactivate(); self.gui.back_button.setEnabled(True)
        GREEN_STYLE = "background-color: #1abc9c;"; RED_STYLE = "background-color: #e74c3c;"; GRAY_STYLE = "background-color: #7f8c8d;"
        if state == 'INITIAL': self.gui.session_button.setText("Bắt đầu Lưu"); self.gui.session_button.setEnabled(False); self.gui.session_button.setStyleSheet(GRAY_STYLE)
        elif state == 'SOLDIER_SELECTED': self.gui.session_button.setText("Bắt đầu Lưu"); self.gui.session_button.setEnabled(True); self.gui.session_button.setStyleSheet(GREEN_STYLE)
        elif state == 'SESSION_ACTIVE':
            self.gui.soldier_selector.setEnabled(False); self.gui.session_button.setText("Kết thúc Phiên tập"); self.gui.session_button.setEnabled(True)
            self.trigger.activate(); self.gui.back_button.setEnabled(False); self.gui.session_button.setStyleSheet(RED_STYLE)
        if self.is_camera_connected: self.trigger.activate()
    def toggle_session_state(self):
        if self.active_session_id: self.end_current_session()
        else: self.start_new_session()
    def start_new_session(self):
        soldier_id = self.gui.soldier_selector.currentData()
        if soldier_id == -1: return
        while True:
            session_name, ok = QInputDialog.getText(self, 'Bắt đầu Phiên tập', 'Nhập tên phiên:', QLineEdit.Normal, f"Phiên tập ngày {datetime.now().strftime('%d-%m')}")
            if not ok: return
            if not session_name.strip(): QMessageBox.warning(self, "Lỗi", "Tên phiên không được để trống."); continue
            if self.db.session_name_exists(session_name.strip(), soldier_id): QMessageBox.warning(self, "Lỗi", f"Tên phiên '{session_name.strip()}' đã tồn tại."); continue
            break
        session_id = self.db.create_session(soldier_id)
        if session_id: self.db.update_session_name(session_id, session_name.strip()); self.active_session_id = session_id; self.set_ui_state('SESSION_ACTIVE')
    def end_current_session(self):
        if not self.active_session_id: return
        shot_count = self.db.get_shot_count_for_session(self.active_session_id)
        if shot_count == 0:
            reply = QMessageBox.question(self, "Xác nhận", "Phiên tập này chưa có phát bắn nào.\n\nThoát và xóa phiên này?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
            else: self.db.delete_session(self.active_session_id)
        else: self.db.end_session(self.active_session_id)
        self.active_session_id = None; self.gui.soldier_selector.setEnabled(True); self.on_soldier_selected(self.gui.soldier_selector.currentIndex())
    def load_soldiers(self):
        self.gui.soldier_selector.clear(); self.gui.soldier_selector.addItem("-- Chọn Người tập --", -1)
        soldiers = self.db.get_all_soldiers()
        if soldiers:
            for soldier in soldiers: self.gui.soldier_selector.addItem(f"{soldier['name']} - {soldier['class_name']}", soldier['id'])
    def on_soldier_selected(self, index):
        if self.active_session_id: return
        soldier_id = self.gui.soldier_selector.itemData(index)
        if soldier_id != -1: self.set_ui_state('SOLDIER_SELECTED')
        else: self.set_ui_state('INITIAL')
    def shutdown_components(self): self.trigger.deactivate(); self.disconnect_camera()
    def start_camera(self):
        num_cameras = count_available_cameras()
        if num_cameras < 2: self.disconnect_camera("Vui lòng kết nối USB camera và nhấn 'Làm mới'")
        else: self.connect_camera(self.configured_camera_index)
    def refresh_camera_connection(self): self.start_camera()
    def connect_camera(self, index: int):
        self.disconnect_camera(); self.cam = Camera(index)
        if not self.cam.isOpened(): self.disconnect_camera(f"Lỗi: Không thể mở Camera index {index}"); return
        is_ok, _ = self.cam.read()
        if is_ok: self.video_timer.start(30); self.is_camera_connected = True; self.trigger.activate()
        else: self.disconnect_camera(f"Lỗi: Không đọc được ảnh từ camera index {index}")
    def disconnect_camera(self, message="Vui lòng kết nối USB camera và nhấn 'Làm mới'"):
        self.video_timer.stop(); self.trigger.deactivate()
        if self.cam: self.cam.release()
        self.cam = None; self.is_camera_connected = False; self.gui.clear_video_feed(message)
    def toggle_calibration_mode(self, force_off=False):
        new_state_is_on = not self.gui.camera_view_label._is_calibrating
        if force_off: new_state_is_on = False
        self.gui.camera_view_label.set_calibration_mode(new_state_is_on)
        self.gui.calibrate_button.setText("HỦY" if new_state_is_on else "HIỆU CHỈNH TÂM")
        if new_state_is_on: QMessageBox.information(self, "Hiệu chỉnh", "Click vào vị trí tâm ngắm mong muốn.")
        elif not force_off: self.calibrated_center = None; logger.info("Người dùng đã hủy hiệu chỉnh.")
    def on_camera_view_clicked(self, point: QPoint):
        if not self.gui.camera_view_label._is_calibrating: return
        pixmap = self.gui.camera_view_label._pixmap
        if not pixmap or pixmap.isNull():
            logger.warning("Không thể hiệu chỉnh vì không có ảnh hiển thị.")
            return
        frame_h, frame_w = self.final_size
        scaled_pixmap = pixmap.scaled(self.gui.camera_view_label.size(), Qt.KeepAspectRatio)
        offset_x = (self.gui.camera_view_label.width() - scaled_pixmap.width()) // 2
        offset_y = (self.gui.camera_view_label.height() - scaled_pixmap.height()) // 2
        if not (offset_x <= point.x() < offset_x + scaled_pixmap.width()): return
        relative_x = (point.x() - offset_x) / scaled_pixmap.width()
        relative_y = (point.y() - offset_y) / scaled_pixmap.height()
        unzoomed_crop_w = frame_w / self.zoom_level; unzoomed_crop_h = frame_h / self.zoom_level
        x_in_zoomed_crop = relative_x * unzoomed_crop_w; y_in_zoomed_crop = relative_y * unzoomed_crop_h
        start_x = (frame_w - unzoomed_crop_w) / 2; start_y = (frame_h - unzoomed_crop_h) / 2
        final_x = start_x + x_in_zoomed_crop; final_y = start_y + y_in_zoomed_crop
        self.calibrated_center = (int(final_x), int(final_y))
        logger.info(f"Hiệu chỉnh tâm thành công. Tọa độ mới trên ảnh gốc: {self.calibrated_center}")
        self.toggle_calibration_mode(force_off=True)
    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    def on_zoom_slider_changed(self, value): self.zoom_level = value / 10.0; self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")