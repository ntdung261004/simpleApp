# file: gui/windows/practice_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication, QInputDialog, QLineEdit
from PySide6.QtCore import QTimer, Signal, Slot, QPoint
import cv2
import numpy as np
import json
import shutil
import sys
import os
import time
from config import APP_DATA_DIR
from datetime import datetime
from PySide6.QtGui import QScreen, QPixmap

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager
from utils.filter import apply_gamma_correction

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_main_menu = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger):
        super().__init__()
        self.setWindowTitle("Phần Mềm Luyện Tập Đường Ngắm Súng Ngắn K54")
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)
        
        self.active_session_id = None
        self.gui = MainGui(); self.setCentralWidget(self.gui)
        self.cam = None; self.final_size = (480, 640); self.zoom_level = 1.0; self.current_gamma = 1.0
        self.calibrated_center = None
        self.is_camera_connected = False; self.shot_counter = 0
        self.frame_read_failures = 0; self.FRAME_FAILURE_THRESHOLD = 5
        self.last_clean_frame = None; self.audio_manager = AudioManager()
        self.video_timer = QTimer(self); self.db_manager = DatabaseManager()
        self.worker = worker; self.bt_trigger = trigger
        
        self._connect_signals()
        
        self.populate_soldier_selector(); self.reset_ui_state(); self.load_config()
        self.training_data_dir = "training_data"
        self.practice_shots_dir = os.path.join(APP_DATA_DIR, "practice_shots")
        os.makedirs(self.training_data_dir, exist_ok=True)
        os.makedirs(self.practice_shots_dir, exist_ok=True)

    def _connect_signals(self):
        # === SỬA LỖI: Xóa kết nối worker.practice_finished ở đây ===
        # Việc kết nối đã được thực hiện tập trung ở main.py
        
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.soldier_selector.currentIndexChanged.connect(self.on_soldier_selection_change)
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.back_button.clicked.connect(self.back_to_main_menu.emit)

    def capture_photo(self):
        """Cho phép bắn ngay khi camera kết nối."""
        if not self.is_camera_connected:
            logger.warning("Bỏ qua trigger: Camera chưa kết nối."); return
        
        frame_to_process = self.last_clean_frame
        if frame_to_process is None:
            logger.error("Không có frame ảnh sạch để xử lý."); return
            
        self.audio_manager.play_sound('shot')
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            training_filename = f"train_{timestamp}.png"
            training_save_path = os.path.join(self.training_data_dir, training_filename)
            cv2.imwrite(training_save_path, frame_to_process)
            
            session_filename = f"shot_{timestamp}.png"
            session_save_path = os.path.join(self.practice_shots_dir, session_filename)
            
            self.request_processing.emit(frame_to_process.copy(), session_save_path, 'practice', self.calibrated_center)
        except Exception as e:
            logger.error(f"Lỗi khi xử lý ảnh sau khi chụp: {e}")

    @Slot(dict)
    def on_processing_finished(self, result):
        """Chỉ lưu vào DB nếu đang trong một phiên tập có người dùng cụ thể."""
        score = result.get('score')
        
        if self.active_session_id is not None:
            self.shot_counter += 1
            self.db_manager.add_shot(
                session_id=self.active_session_id, shot_number=self.shot_counter,
                score=score, target_detected=result.get('target_detected_raw'),
                coords=result.get('coords'), image_path=result.get('image_path')
            )
        
        if score is not None and score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')
        
        self.gui.update_results(
            time_str=result.get('time_str'), target_name=result.get('target_name'),
            score=score, result_frame=result.get('result_frame')
        )

    def toggle_session(self):
        """Bắt đầu hoặc kết thúc một phiên LƯU TRỮ."""
        if self.active_session_id is not None: # Đang trong phiên -> Kết thúc
            shot_count = self.db_manager.get_shot_count_for_session(self.active_session_id)
            if shot_count == 0:
                reply = QMessageBox.question(self, "Xác nhận", "Phiên tập trống, có muốn xóa không?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.Yes: self.db_manager.delete_session(self.active_session_id)
                self.finalize_session()
            else:
                current_soldier = self.gui.soldier_selector.currentData()
                soldier_id = current_soldier['id']
                while True:
                    default_name = f"Phiên tập #{self.active_session_id}"; session_name, ok = QInputDialog.getText(self, "Đặt tên Phiên tập", "Nhập tên để lưu:", QLineEdit.Normal, default_name)
                    if not ok: return
                    final_name = session_name.strip() if session_name.strip() else default_name
                    if not self.db_manager.session_name_exists(final_name, soldier_id=soldier_id, exclude_session_id=self.active_session_id):
                        self.db_manager.update_session_name(self.active_session_id, final_name); self.finalize_session(); break
                    else: QMessageBox.warning(self, "Tên bị trùng", f"Người tập này đã có phiên tập tên '{final_name}'.\nVui lòng chọn một tên khác.")
        else: # Chưa trong phiên -> Bắt đầu
            selected_soldier = self.gui.soldier_selector.currentData()
            if not selected_soldier:
                QMessageBox.warning(self, "Chưa chọn Người tập", "Vui lòng chọn một người tập từ danh sách để bắt đầu lưu phiên.")
                return

            self.active_session_id = self.db_manager.create_session(selected_soldier['id'])
            if self.active_session_id:
                self.shot_counter = 0; self.gui.clear_results_list()
                self.gui.session_button.setText("KẾT THÚC LƯU"); self.gui.session_button.setObjectName("danger"); self.gui.style().polish(self.gui.session_button)
                self.gui.back_button.setEnabled(False); self.gui.soldier_selector.setEnabled(False)

    def finalize_session(self):
        if self.active_session_id: self.db_manager.end_session(self.active_session_id)
        self.active_session_id = None
        self.gui.session_button.setText("BẮT ĐẦU LƯU"); self.gui.session_button.setObjectName("start_button"); self.gui.style().polish(self.gui.session_button)
        self.gui.back_button.setEnabled(True); self.gui.soldier_selector.setEnabled(True)

    def populate_soldier_selector(self):
        self.gui.soldier_selector.clear()
        self.gui.soldier_selector.addItem("--- Chọn người tập để lưu ---", userData=None)
        soldiers = self.db_manager.get_all_soldiers()
        for soldier in soldiers:
            self.gui.soldier_selector.addItem(f"{soldier.get('name')} - {soldier.get('class_name')}", userData=soldier)

    def on_soldier_selection_change(self):
        if self.active_session_id is not None:
            self.finalize_session()
        self.gui.clear_results_list()

    def reset_ui_state(self):
        self.finalize_session()
        self.gui.clear_results_list()
        self.gui.time_label.setText("Thời gian: --:--:--"); self.gui.target_name_label.setText("Tên mục tiêu: --"); self.gui.score_label.setText("Điểm số: --")
        self.gui.result_image_label.setText("Chưa có ảnh kết quả"); self.gui.result_image_label.setPixmap(QPixmap())

    def shutdown_components(self): self.disconnect_camera(); self.bt_trigger.deactivate(); self.reset_ui_state()
    def start_camera(self): self.populate_soldier_selector(); self.bt_trigger.activate(); self.refresh_camera_connection()
    
    def update_frame(self):
        if not (self.cam and self.cam.isOpened()): return
        ret, frame = self.cam.read()
        if not ret or frame is None:
            self.frame_read_failures += 1
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD: self.disconnect_camera("Mất kết nối")
            return
        self.frame_read_failures = 0; self.is_camera_connected = True
        processed_frame = self.crop_and_resize_frame(frame); self.last_clean_frame = processed_frame.copy()
        filtered_frame = apply_gamma_correction(self.last_clean_frame, gamma=self.current_gamma)
        zoomed_frame = self.apply_digital_zoom(filtered_frame, self.zoom_level)
        frame_to_display = zoomed_frame.copy()
        point_to_draw = self.calculate_center_on_zoom(processed_frame)
        if point_to_draw: cv2.drawMarker(frame_to_display, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
        self.gui.display_frame(frame_to_display)
    
    def calculate_center_on_zoom(self, original_frame):
        h, w, _ = original_frame.shape
        center = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        start_x = (w - int(w / self.zoom_level)) // 2; start_y = (h - int(h / self.zoom_level)) // 2
        if center[0] >= start_x and center[1] >= start_y:
            zoomed_cx = int((center[0] - start_x) * self.zoom_level); zoomed_cy = int((center[1] - start_y) * self.zoom_level)
            return (zoomed_cx, zoomed_cy)
        return None

    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    def on_zoom_changed(self, value): self.zoom_level = value / 10.0
    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape; target_aspect_ratio = self.final_size[1] / self.final_size[0]
        new_w = int(h * target_aspect_ratio); start_x = (w - new_w) // 2
        return cv2.resize(frame[:, start_x : start_x + new_w], self.final_size, interpolation=cv2.INTER_AREA)
    def apply_digital_zoom(self, frame, zoom):
        if zoom <= 1.0: return frame
        h, w, _ = frame.shape; crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
        return cv2.resize(frame[start_y : start_y + crop_h, start_x : start_x + crop_w], (w, h), interpolation=cv2.INTER_LINEAR)
    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")
    def set_new_center(self, click_pos: QPoint):
        widget_size = self.gui.camera_view_label.size(); img_w, img_h = self.final_size
        scale = min(widget_size.width() / img_w, widget_size.height() / img_h)
        display_w, display_h = int(img_w * scale), int(img_h * scale)
        offset_x, offset_y = (widget_size.width() - display_w) // 2, (widget_size.height() - display_h) // 2
        if not (offset_x <= click_pos.x() < offset_x + display_w and offset_y <= click_pos.y() < offset_y + display_h): return
        click_x = int((click_pos.x() - offset_x) / scale); click_y = int((click_pos.y() - offset_y) / scale)
        start_x = (img_w - int(img_w / self.zoom_level)) // 2; start_y = (img_h - int(img_h / self.zoom_level)) // 2
        final_x = int(start_x + (click_x / self.zoom_level)); final_y = int(start_y + (click_y / self.zoom_level))
        self.calibrated_center = (final_x, final_y); self.toggle_calibration_mode()
    def connect_camera(self, index):
        self.disconnect_camera(); self.cam = Camera(index)
        if not self.cam.isOpened(): self.disconnect_camera(f"Lỗi: Không thể mở Camera {index}"); return
        is_ok = any(self.cam.read()[0] for _ in range(10))
        if is_ok: self.video_timer.start(30)
        else: self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")
    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None; self.is_camera_connected = False; self.gui.clear_video_feed(message)
    def refresh_camera_connection(self):
        all_cameras = find_available_cameras()
        if len(all_cameras) >= 1: self.connect_camera(self.configured_camera_index)
        else: self.disconnect_camera(message="Không tìm thấy camera")
    def load_config(self):
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding='utf-8') as f: config = json.load(f)
                self.configured_camera_index = int(config.get("camera_index", 0))
        except Exception as e: self.configured_camera_index = 0