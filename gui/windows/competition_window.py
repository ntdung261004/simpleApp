# file: gui/windows/competition_window.py
import logging
from datetime import datetime
import json
import os
from PySide6.QtWidgets import QMainWindow, QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QFont, QPixmap
import numpy as np
import cv2

from ..ui.ui_competition import CompetitionGui
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from core.database import DatabaseManager
from utils.audio import AudioManager
from utils.filter import apply_gamma_correction
from utils.camera import Camera, count_available_cameras
from config import APP_DATA_DIR
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class ParticipantItemWidget(QWidget): # Giữ nguyên
    def __init__(self, name: str, class_name: str, parent=None):
        super().__init__(parent); self.setObjectName("ParticipantItemWidget"); self.setStyleSheet(""" #ParticipantItemWidget { background-color: transparent; } QLabel { color: white; background-color: transparent; } #status_label { padding: 5px; border-radius: 3px; font-weight: bold; } """)
        main_layout = QHBoxLayout(self); icon_label = QLabel(); icon_label.setFixedSize(32, 32); icon_path = resource_path("assets/images/icon/user_icon.png"); icon_label.setPixmap(QPixmap(icon_path)); icon_label.setScaledContents(True)
        info_layout = QVBoxLayout(); info_layout.setSpacing(0); name_label = QLabel(f"<b>{name}</b>"); class_label = QLabel(class_name); info_layout.addWidget(name_label); info_layout.addWidget(class_label)
        self.status_label = QLabel("Chưa bắn"); self.status_label.setObjectName("status_label"); self.status_label.setStyleSheet("background-color: #95a5a6; color: #2c3e50;"); self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.status_label)
    def set_status(self, status: str):
        text, color, text_color = "Lỗi", "#e74c3c", "white"
        if status == 'waiting': text, color, text_color = "Chưa bắn", "#95a5a6", "#2c3e50"
        elif status == 'shooting': text, color, text_color = "Đang bắn...", "#f1c40f", "#2c3e50"
        elif status == 'finished': text, color, text_color = "Hoàn thành", "#2ecc71", "white"
        self.status_label.setText(text); self.status_label.setStyleSheet(f"background-color: {color}; color: {text_color};")

class CompetitionWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_menu_signal = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger, config: dict):
        super().__init__()
        self.setWindowTitle("Chế Độ Thi Đấu")
        self.gui = CompetitionGui(); self.setCentralWidget(self.gui)
        self.configured_camera_index = config.get('camera_index', 0)
        self.db = DatabaseManager(); self.trigger = trigger
        self.worker = worker; self.audio_manager = AudioManager()
        
        self.cam = None; self.final_size = (640, 480); self.zoom_level = 1.0
        self.video_timer = QTimer(self); self.video_timer.timeout.connect(self.update_frame)
        self.competition_data = None; self.current_shooter_index = -1; self.current_shot_count = 0
        self.is_camera_connected = False; self.calibrated_center = None
        self.current_gamma = 1.0; self._setup_connections()

    def _crop_frame_to_3_4(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]; target_aspect = 3.0 / 4.0
        new_w = int(h * target_aspect)
        if new_w > w: return frame
        start_x = (w - new_w) // 2
        return frame[:, start_x : start_x + new_w]
        
    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: return
        ret, frame = self.cam.read()
        if not ret: self.disconnect_camera("Mất kết nối với camera.\nVui lòng kiểm tra và nhấn 'Làm mới'."); return
        frame_cropped = self._crop_frame_to_3_4(frame)
        frame_resized = cv2.resize(frame_cropped, (self.final_size[1], self.final_size[0]))
        processed_frame = self.process_frame_for_display(frame_resized)
        self.gui.display_frame(processed_frame)

    def process_frame_for_display(self, frame: np.ndarray) -> np.ndarray:
        if self.current_gamma != 1.0: frame = apply_gamma_correction(frame, self.current_gamma)
        h, w, _ = frame.shape
        original_center_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        if self.zoom_level > 1.0:
            zoomed_w = int(w / self.zoom_level); zoomed_h = int(h / self.zoom_level)
            crop_start_x = (w - zoomed_w) // 2; crop_start_y = (h - zoomed_h) // 2
            transformed_center_x = original_center_point[0] - crop_start_x
            transformed_center_y = original_center_point[1] - crop_start_y
            scale_factor = w / zoomed_w
            final_center_point = (int(transformed_center_x * scale_factor), int(transformed_center_y * scale_factor))
            frame = frame[crop_start_y : crop_start_y + zoomed_h, crop_start_x : crop_start_x + zoomed_w]
            frame = cv2.resize(frame, (w, h))
        else:
            final_center_point = original_center_point
        cv2.drawMarker(frame, final_center_point, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        return frame

    # === BẮT ĐẦU VÙNG SỬA LỖI LOGIC HIỆU CHỈNH TÂM ===
    def toggle_calibration_mode(self):
        is_entering_calibration = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_entering_calibration)
        self.gui.calibrate_button.setText("HỦY" if is_entering_calibration else "HIỆU CHỈNH TÂM")
        if is_entering_calibration:
            QMessageBox.information(self, "Hiệu chỉnh tâm", "Click vào vị trí tâm ngắm mong muốn trên màn hình camera.")
        else:
            self.calibrated_center = None
            logger.info("Người dùng đã hủy hiệu chỉnh. Tâm ngắm được reset về trung tâm.")

    def on_camera_view_clicked(self, point: QPoint):
        if not self.gui.camera_view_label._is_calibrating: return

        view_w = self.gui.camera_view_label.width(); frame_h, frame_w = self.final_size
        pixmap = self.gui.camera_view_label._pixmap
        if pixmap.isNull(): return
        scaled_pixmap = pixmap.scaled(self.gui.camera_view_label.size(), Qt.KeepAspectRatio)
        offset_x = (view_w - scaled_pixmap.width()) // 2
        if not (offset_x <= point.x() < offset_x + scaled_pixmap.width()): return
        scale_ratio = scaled_pixmap.width() / frame_w
        click_on_frame_x = (point.x() - offset_x) / scale_ratio
        click_on_frame_y = (point.y() - (self.gui.camera_view_label.height() - scaled_pixmap.height()) // 2) / scale_ratio
        zoomed_w = frame_w / self.zoom_level; zoomed_h = frame_h / self.zoom_level
        x_in_zoomed_crop = click_on_frame_x * (zoomed_w / frame_w); y_in_zoomed_crop = click_on_frame_y * (zoomed_h / frame_h)
        start_x = (frame_w - zoomed_w) / 2; start_y = (frame_h - zoomed_h) / 2
        
        self.calibrated_center = (int(start_x + x_in_zoomed_crop), int(start_y + y_in_zoomed_crop))
        logger.info(f"Hiệu chỉnh tâm thành công. Tọa độ mới: {self.calibrated_center}")
        
        self.gui.camera_view_label.set_calibration_mode(False)
        self.gui.calibrate_button.setText("HIỆU CHỈNH TÂM")
    # === KẾT THÚC VÙNG SỬA LỖI ===
        
    # --- Các hàm logic còn lại (không thay đổi) ---
    def _setup_connections(self):
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.start_turn_button.clicked.connect(self.start_current_turn)
        self.gui.back_button.clicked.connect(self.confirm_end_competition)
    def start_camera(self):
        num_cameras = count_available_cameras()
        if num_cameras < 2: self.disconnect_camera("Vui lòng kết nối USB camera và nhấn 'Làm mới'")
        else: self.connect_camera(self.configured_camera_index)
    def refresh_camera_connection(self): self.start_camera()
    def connect_camera(self, index: int):
        self.disconnect_camera(); self.cam = Camera(index)
        if not self.cam.isOpened(): self.disconnect_camera(f"Lỗi: Không thể mở Camera index {index}"); return
        is_ok, _ = self.cam.read()
        if is_ok: self.video_timer.start(30); self.is_camera_connected = True
        else: self.disconnect_camera(f"Lỗi: Không đọc được ảnh từ camera index {index}")
    def disconnect_camera(self, message="Vui lòng kết nối USB camera và nhấn 'Làm mới'"):
        self.video_timer.stop();
        if self.cam: self.cam.release()
        self.cam = None; self.is_camera_connected = False; self.gui.clear_video_feed(message)
    def setup_competition(self, competition_id: int, participants: list):
        self.competition_data = {'id': competition_id, 'participants': [{'id': p['id'], 'name': p['name'], 'class_name': p['class_name'], 'shots': [], 'total_score': 0, 'status': 'waiting'} for p in participants]}; self.current_shooter_index = -1; self.current_shot_count = 0; self.next_shooter()
    def _update_participant_list(self):
        self.gui.participants_list.clear();
        if not self.competition_data: return
        for idx, p in enumerate(self.competition_data['participants']):
            widget = ParticipantItemWidget(p['name'], p['class_name']); widget.set_status(p['status']); item = QListWidgetItem(); item.setSizeHint(widget.sizeHint()); self.gui.participants_list.addItem(item); self.gui.participants_list.setItemWidget(item, widget)
            if idx == self.current_shooter_index: item.setSelected(True)
    def next_shooter(self):
        if not self.competition_data: return
        if self.current_shooter_index >= 0: self.competition_data['participants'][self.current_shooter_index]['status'] = 'finished'
        self.current_shooter_index += 1
        if self.current_shooter_index >= len(self.competition_data['participants']): self.end_competition(); return
        shooter = self.competition_data['participants'][self.current_shooter_index]; shooter['status'] = 'shooting'; self.current_shot_count = 0
        self.gui.shooter_name_label.setText(f"Tên: {shooter['name']}"); self.gui.shooter_class_label.setText(f"Đơn vị: {shooter['class_name']}")
        self._reset_scoreboard(); self._update_participant_list(); self.gui.score_stack.setCurrentWidget(self.gui.score_stack.widget(0)); self.trigger.deactivate()
    def start_current_turn(self): self.gui.score_stack.setCurrentWidget(self.gui.score_stack.widget(1)); self.trigger.activate()
    @Slot(dict, object)
    def handle_processing_result(self, result: dict, shooter_data: object):
        if not self.competition_data or shooter_data['id'] != self.competition_data['participants'][self.current_shooter_index]['id']: return
        self.audio_manager.play_score(result.get('score')); self.current_shot_count += 1; score = result.get('score', 0); self.competition_data['participants'][self.current_shooter_index]['shots'].append(score); self._update_scoreboard(self.current_shot_count, score)
        self.db.add_competition_shot(competition_id=self.competition_data['id'], shooter_id=shooter_data['id'], score=score, coords=json.dumps(result.get('coords')), image_path=result.get('image_path'), target_name=result.get('target_detected_raw', 'N/A'))
        if self.current_shot_count >= 12: self.trigger.deactivate(); self.next_shooter()
    def confirm_end_competition(self):
        if QMessageBox.question(self, "Kết thúc", "Bạn có chắc muốn kết thúc cuộc thi?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes: self.end_competition()
    def end_competition(self): self.trigger.deactivate(); self.shutdown_components(); self.back_to_menu_signal.emit()
    def shutdown_components(self): self.trigger.deactivate(); self.disconnect_camera()
    @Slot()
    def handle_shot(self):
        if not self.is_camera_connected or self.current_shot_count >= 12 or not self.trigger.is_active: return
        ret, frame = self.cam.read()
        if ret and frame is not None:
            self.audio_manager.play_sound('shot'); frame_cropped = self._crop_frame_to_3_4(frame)
            frame_resized = cv2.resize(frame_cropped, (self.final_size[1], self.final_size[0]))
            image_dir = os.path.join(APP_DATA_DIR, 'history_images', f"comp_{self.competition_data['id']}"); os.makedirs(image_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f"); current_shooter = self.competition_data['participants'][self.current_shooter_index]; image_path = os.path.join(image_dir, f"shot_{current_shooter['id']}_{timestamp}.jpg")
            self.request_processing.emit(frame_resized, image_path, 'competition', current_shooter)
    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    def on_zoom_slider_changed(self, value): self.zoom_level = value / 10.0; self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")
    def _update_scoreboard(self, shot_number, score):
        if 1 <= shot_number <= 3: self.gui.target_1_score_label.setText(f"Điểm: {score}")
        elif 4 <= shot_number <= 6: self.gui.target_2_score_label.setText(f"Điểm: {score}")
        elif 7 <= shot_number <= 9: self.gui.target_3_score_label.setText(f"Điểm: {score}")
        elif 10 <= shot_number <= 12: self.gui.target_4_score_label.setText(f"Điểm: {score}")
        total_score = sum(self.competition_data['participants'][self.current_shooter_index]['shots']); self.gui.total_score_label.setText(f"Tổng điểm: {total_score}"); self.gui.ammo_count_label.setText(f"Số đạn còn lại: {12 - shot_number}/12")
    def _reset_scoreboard(self):
        self.gui.target_1_score_label.setText("Điểm: --"); self.gui.target_2_score_label.setText("Điểm: --"); self.gui.target_3_score_label.setText("Điểm: --"); self.gui.target_4_score_label.setText("Điểm: --")
        self.gui.total_score_label.setText("Tổng điểm: 0"); self.gui.ammo_count_label.setText("Số đạn còn lại: 12/12")