# file: gui/windows/competition_window.py
import logging
from datetime import datetime
import json
import os
import time
from PySide6.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout, QLabel
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
from utils.camera import Camera, find_available_cameras
from config import APP_DATA_DIR
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class ParticipantItemWidget(QWidget):
    def __init__(self, name: str, class_name: str, parent=None):
        super().__init__(parent); self.setObjectName("ParticipantItemWidget")
        self.setStyleSheet(""" #ParticipantItemWidget { background-color: transparent; } QLabel { color: white; background-color: transparent; } #status_label { padding: 5px; border-radius: 3px; font-weight: bold; } """)
        main_layout = QHBoxLayout(self); icon_label = QLabel(); icon_label.setFixedSize(32, 32)
        icon_path = resource_path("assets/images/icon/user_icon.png")
        icon_label.setPixmap(QPixmap(icon_path)); icon_label.setScaledContents(True)
        info_layout = QVBoxLayout(); name_label = QLabel(name); class_name_label = QLabel(class_name)
        info_layout.addWidget(name_label); info_layout.addWidget(class_name_label)
        self.status_label = QLabel(); self.status_label.setObjectName("status_label")
        main_layout.addWidget(icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.status_label)
        self.set_status("pending")

    def set_status(self, status: str):
        if status == "finished": self.status_label.setText("HOÀN THÀNH"); self.status_label.setStyleSheet("background-color: #27ae60; color: white;")
        elif status == "competing": self.status_label.setText("ĐANG BẮN"); self.status_label.setStyleSheet("background-color: #3498db; color: white;")
        else: self.status_label.setText("CHỜ"); self.status_label.setStyleSheet("background-color: #f39c12; color: white;")

class CompetitionWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_menu_signal = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger):
        super().__init__()
        self.gui = CompetitionGui(); self.setCentralWidget(self.gui)
        self.db = DatabaseManager(); self.processing_worker = worker
        self.bt_trigger = trigger; self.audio_manager = AudioManager()
        self.competition_id = None; self.participants = []
        self.current_shooter_index = -1; self.current_participant_id = None
        self.is_turn_active = False; self.current_shots_data = []
        self.MAX_AMMO = 4
        self.cam = None; self.video_timer = QTimer(self)
        self.final_size = (640, 480); self.zoom_level = 1.0; self.current_gamma = 1.0
        self.calibrated_center = None; self.is_camera_connected = False
        self.frame_read_failures = 0; self.FRAME_FAILURE_THRESHOLD = 5
        self.last_clean_frame = None; self.configured_camera_index = 0
        self._connect_signals(); self.load_config()
        self.gui.start_turn_button.setEnabled(False)

    def _connect_signals(self):
        self.processing_worker.competition_finished.connect(self.handle_processing_result)
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        self.gui.participants_list.itemClicked.connect(self.on_participant_selected)
        self.gui.start_turn_button.clicked.connect(self.start_current_turn)
        self.gui.back_button.clicked.connect(self._handle_exit_request)

    def setup_competition(self, competition_id: int, participants: list):
        self.competition_id = competition_id; self.participants = participants; self.current_shooter_index = -1; self.current_participant_id = None; self.is_turn_active = False
        self.bt_trigger.deactivate(); self.gui.participants_list.clear()
        for shooter in self.participants:
            widget = ParticipantItemWidget(name=shooter['name'], class_name=shooter['class_name'])
            item = QListWidgetItem(); item.setSizeHint(widget.sizeHint()); item.setData(Qt.UserRole, shooter['id'])
            self.gui.participants_list.addItem(item); self.gui.participants_list.setItemWidget(item, widget)
        self.gui.participants_list.setCurrentRow(-1); self.gui.score_stack.setCurrentIndex(0)
    
    @Slot(QListWidgetItem)
    def on_participant_selected(self, item: QListWidgetItem):
        self.current_shooter_index = self.gui.participants_list.row(item); shooter_info = self.participants[self.current_shooter_index]
        widget = self.gui.participants_list.itemWidget(item)
        if widget.status_label.text() != "HOÀN THÀNH":
            self.gui.start_turn_button.setEnabled(True); self.gui.start_turn_button.setText(f"BẮT ĐẦU LƯỢT CỦA\n{shooter_info['name']}")
        else: self.gui.start_turn_button.setEnabled(False); self.gui.start_turn_button.setText("ĐÃ HOÀN THÀNH")

    @Slot()
    def start_current_turn(self):
        if self.current_shooter_index == -1: return
        shooter_info = self.participants[self.current_shooter_index]
        self.current_participant_id = self.db.get_participant_id(self.competition_id, shooter_info['id'])
        if self.current_participant_id is None: QMessageBox.critical(self, "Lỗi Dữ liệu", f"Không thể xác định lượt thi của {shooter_info['name']}."); return
        item = self.gui.participants_list.item(self.current_shooter_index); widget = self.gui.participants_list.itemWidget(item)
        if widget: widget.set_status("competing")
        self.current_shots_data = []; self.gui.score_stack.setCurrentIndex(1)
        self.gui.shooter_name_label.setText(f"Tên: {shooter_info['name']}"); self.gui.shooter_class_label.setText(f"Đơn vị: {shooter_info['class_name']}")
        self._update_scoreboard(); self.gui.participants_list.setEnabled(False); self.gui.start_turn_button.setEnabled(False)
        self.is_turn_active = True; self.bt_trigger.activate()

    def end_current_turn_with_popup(self):
        self.is_turn_active = False; self.bt_trigger.deactivate(); total_score = sum(shot.get('score', 0) for shot in self.current_shots_data)
        msg_box = QMessageBox(self); msg_box.setWindowTitle("Hoàn thành lượt bắn"); msg_box.setText(f"Tổng điểm lượt bắn: {total_score}/{self.MAX_AMMO * 10}")
        save_button = msg_box.addButton("Lưu và Tiếp tục", QMessageBox.AcceptRole); retry_button = msg_box.addButton("Bắn lại", QMessageBox.DestructiveRole); msg_box.exec()
        if msg_box.clickedButton() == save_button: self._save_and_continue()
        elif msg_box.clickedButton() == retry_button: self._retry_turn()

    def _save_and_continue(self):
        item = self.gui.participants_list.item(self.current_shooter_index); widget = self.gui.participants_list.itemWidget(item)
        if widget: widget.set_status("finished")
        self._reset_turn_state()

    def _retry_turn(self):
        self.db.delete_shots_for_participant(self.competition_id, self.current_participant_id); self.current_shots_data = []; self._update_scoreboard()
        self.is_turn_active = True; self.bt_trigger.activate()

    def _reset_turn_state(self):
        self.gui.participants_list.setEnabled(True); self.gui.participants_list.setCurrentRow(-1)
        self.gui.start_turn_button.setText("CHỌN NGƯỜI BẮN"); self.gui.start_turn_button.setEnabled(False)
        self.gui.score_stack.setCurrentIndex(0); self.current_shooter_index = -1; self.current_participant_id = None
        self.is_turn_active = False; self.bt_trigger.deactivate()

    def handle_shot(self):
        if not self.is_turn_active or not self.is_camera_connected or self.last_clean_frame is None: return
        self.is_turn_active = False; self.audio_manager.play_sound('shot')
        context = {'participant_id': self.current_participant_id, 'calibrated_center': self.calibrated_center}
        save_dir = os.path.join(APP_DATA_DIR, "competition_shots"); os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f"); image_name = f"shot_{self.competition_id}_{self.current_participant_id}_{timestamp}.jpg"
        image_path = os.path.join(save_dir, image_name)
        self.request_processing.emit(self.last_clean_frame.copy(), image_path, 'competition', context)

    @Slot(dict, object)
    def handle_processing_result(self, result: dict, context: dict):
        if not context or context.get('participant_id') != self.current_participant_id: self.is_turn_active = True; return
        score = result.get('score')
        if score is not None and score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')
        cv2.imwrite(result.get('image_path'), result.get('result_frame'))
        self.db.add_competition_shot(competition_id=self.competition_id, participant_id=context['participant_id'], score=score, coords=result.get('coords'), image_path=result.get('image_path'))
        self.current_shots_data.append(result); self._update_scoreboard()
        if len(self.current_shots_data) >= self.MAX_AMMO: self.end_current_turn_with_popup()
        else: self.is_turn_active = True

    def _update_scoreboard(self):
        ammo_shot = len(self.current_shots_data)
        labels = [self.gui.target_1_score_label, self.gui.target_2_score_label, self.gui.target_3_score_label, self.gui.target_4_score_label]
        for i, label in enumerate(labels):
            if i < ammo_shot: label.setText(f"Điểm: {self.current_shots_data[i].get('score', 0)}")
            else: label.setText("Điểm: --")
        total_score = sum(shot.get('score', 0) for shot in self.current_shots_data)
        self.gui.total_score_label.setText(f"Tổng điểm: {total_score}"); self.gui.ammo_count_label.setText(f"Số đạn đã bắn: {ammo_shot}/{self.MAX_AMMO}")
    
    def _handle_exit_request(self):
        if self.is_turn_active:
            reply = QMessageBox.warning(self, "Xác nhận Thoát", "Lượt bắn đang diễn ra. Bạn có chắc chắn muốn thoát?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No: return
        self.shutdown_components(); self.back_to_menu_signal.emit()

    def shutdown_components(self): self.disconnect_camera(); self.bt_trigger.deactivate()
    def start_camera(self): self.refresh_camera_connection()

    @Slot(int)
    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    
    @Slot(int)
    def on_zoom_changed(self, value): self.zoom_level = value / 10.0; self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")

    # === BẮT ĐẦU SỬA LỖI: SỬA LẠI CÚ PHÁP IF ===
    def update_frame(self):
        if not (self.cam and self.cam.isOpened()): return
        
        ret, frame = self.cam.read()
        
        # Sửa lại khối if-else cho đúng cú pháp
        if not ret or frame is None:
            self.frame_read_failures += 1
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD:
                self.disconnect_camera("Mất kết nối")
            return
            
        self.frame_read_failures = 0
        self.is_camera_connected = True
        
        processed_frame = self.crop_and_resize_frame(frame)
        self.last_clean_frame = processed_frame.copy()
        filtered_frame = apply_gamma_correction(self.last_clean_frame, gamma=self.current_gamma)
        zoomed_frame = self.apply_digital_zoom(filtered_frame, self.zoom_level)
        frame_to_display = zoomed_frame.copy()
        point_to_draw = self.calculate_center_on_zoom(processed_frame)
        if point_to_draw: cv2.drawMarker(frame_to_display, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
        self.gui.display_frame(frame_to_display)
    # === KẾT THÚC SỬA LỖI ===

    def calculate_center_on_zoom(self, original_frame):
        h, w, _ = original_frame.shape
        center = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        start_x = (w - int(w / self.zoom_level)) // 2; start_y = (h - int(h / self.zoom_level)) // 2
        if center[0] >= start_x and center[1] >= start_y:
            zoomed_cx = int((center[0] - start_x) * self.zoom_level); zoomed_cy = int((center[1] - start_y) * self.zoom_level)
            return (zoomed_cx, zoomed_cy)
        return None

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
        self.video_timer.stop();
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
        except Exception: self.configured_camera_index = 0