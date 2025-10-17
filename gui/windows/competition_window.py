# file: gui/windows/competition_window.py
import logging
from datetime import datetime
import json
import os
from PySide6.QtWidgets import QMainWindow, QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QMessageBox
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QPixmap
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


# === BẮT ĐẦU VÙNG THAY ĐỔI GIAO DIỆN ===
class ParticipantItemWidget(QWidget):
    """
    Widget tùy chỉnh cho mỗi người tham gia trong danh sách thi đấu.
    Giao diện được làm lại để tương đồng với màn hình Setup.
    """
    def __init__(self, name: str, class_name: str, parent=None):
        super().__init__(parent)
        # 1. Áp dụng style card-view, bỏ viền chữ, thu nhỏ thẻ trạng thái
        self.setStyleSheet("""
            QWidget {
                background-color: #34495e;
                border-radius: 8px;
            }
            QLabel {
                color: white;
                background-color: transparent;
                border: none;
            }
            #status_label {
                font-size: 11px;
                font-weight: bold;
                padding: 3px 10px;
                border-radius: 5px;
            }
        """)

        main_layout = QHBoxLayout(self)
        # 2. Thêm margin để nội dung không bị sát viền
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # Icon (giữ nguyên)
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setPixmap(QPixmap(resource_path("assets/images/icon/user_icon.png")))
        icon_label.setScaledContents(True)

        # Thông tin người bắn (giữ nguyên)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        name_label = QLabel(f"<b>{name}</b>")
        class_label = QLabel(class_name)
        class_label.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(class_label)

        # Thẻ trạng thái
        self.status_label = QLabel("Chưa bắn")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)

        main_layout.addWidget(icon_label)
        main_layout.addLayout(info_layout, 1)
        main_layout.addWidget(self.status_label)

    def set_status(self, status: str):
        # 3. Cập nhật lại text và màu sắc cho thẻ trạng thái mới
        text, color, text_color = {
            "waiting": ("CHỜ", "#7f8c8d", "white"),
            "shooting": ("ĐANG BẮN", "#f39c12", "#2c3e50"),
            "finished": ("HOÀN THÀNH", "#27ae60", "white")
        }.get(status, ("LỖI", "#c0392b", "white"))

        self.status_label.setText(text)
        self.status_label.setStyleSheet(
            f"background-color: {color}; color: {text_color};"
            "font-size: 11px; font-weight: bold; padding: 3px 10px; border-radius: 5px;"
        )
# === KẾT THÚC VÙNG THAY ĐỔI GIAO DIỆN ===


class CompetitionWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_menu_signal = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger, config: dict):
        super().__init__(); self.gui = CompetitionGui(); self.setCentralWidget(self.gui)
        self.setWindowTitle("Chế Độ Thi Đấu")
        self.configured_camera_index = config.get('camera_index', 0)
        self.db = DatabaseManager(); self.trigger = trigger; self.worker = worker; self.audio_manager = AudioManager()
        self.cam = None; self.final_size = (640, 480); self.zoom_level = 1.0; self.current_gamma = 1.0
        self.video_timer = QTimer(self); self.video_timer.timeout.connect(self.update_frame)
        self.competition_data = None; self.current_shooter_index = -1; self.current_shot_count = 0
        self.is_camera_connected = False; self.calibrated_center = None; self._setup_connections()

    def _setup_connections(self):
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed); self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode); self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection); self.gui.start_turn_button.clicked.connect(self.start_current_turn)
        self.gui.back_button.clicked.connect(self.confirm_end_competition)

    def _crop_frame_to_3_4(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]; new_w = int(h * 3.0/4.0); start_x = (w - new_w) // 2
        return frame[:, start_x : start_x + new_w] if new_w <= w else frame

    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: return
        ret, frame = self.cam.read()
        if not ret: self.disconnect_camera("Mất kết nối camera."); return
        frame_resized = cv2.resize(self._crop_frame_to_3_4(frame), (self.final_size[1], self.final_size[0]))
        self.gui.display_frame(self.process_frame_for_display(frame_resized))

    def process_frame_for_display(self, frame: np.ndarray) -> np.ndarray:
        processed_frame = apply_gamma_correction(frame, self.current_gamma) if self.current_gamma != 1.0 else frame.copy()
        h, w, _ = processed_frame.shape; center_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        if self.zoom_level > 1.0:
            new_w, new_h = int(w / self.zoom_level), int(h / self.zoom_level)
            start_x, start_y = (w - new_w) // 2, (h - new_h) // 2
            display_center_x = (center_point[0] - start_x) * self.zoom_level; display_center_y = (center_point[1] - start_y) * self.zoom_level
            processed_frame = cv2.resize(processed_frame[start_y:start_y+new_h, start_x:start_x+new_w], (w, h))
            center_point = (int(display_center_x), int(display_center_y))
        cv2.drawMarker(processed_frame, center_point, (0, 0, 255), cv2.MARKER_CROSS, 20, 2); return processed_frame

    def setup_competition(self, competition_id: int, competition_name: str, participants: list):
        self.setWindowTitle(f"Thi Đấu - {competition_name}")
        self.competition_data = {
            'id': competition_id,
            'name': competition_name,
            'participants': [
                {'id': p['id'], 'name': p['name'], 'class_name': p['class_name'], 'shots': [], 'total_score': 0, 'status': 'waiting'}
                for p in participants
            ]
        }
        self.current_shooter_index = -1; self.current_shot_count = 0; self.next_shooter()

    @Slot(dict, object)
    def handle_processing_result(self, result: dict, shooter_data: dict):
        current_shooter = self.competition_data['participants'][self.current_shooter_index]
        if not self.competition_data or shooter_data['id'] != current_shooter['id']: return
        
        self.current_shot_count += 1
        score = result.get('score', 0); self.audio_manager.play_score(score)
        current_shooter['shots'].append(score); self._update_scoreboard(self.current_shot_count, score)
        
        self.db.add_competition_shot(
            competition_id=self.competition_data['id'], soldier_id=shooter_data['id'],
            score=score, coords=result.get('coords'), image_path=result.get('image_path'),
            target_name=result.get('target_detected_raw', 'N/A')
        )
        if self.current_shot_count >= 10: self.trigger.deactivate(); self.next_shooter()

    @Slot()
    def handle_shot(self):
        if not self.is_camera_connected or self.current_shot_count >= 10 or not self.trigger.is_active: return
        ret, frame = self.cam.read()
        if ret and frame is not None:
            self.audio_manager.play_sound('shot')
            frame_resized = cv2.resize(self._crop_frame_to_3_4(frame), (self.final_size[1], self.final_size[0]))
            
            image_dir = os.path.join(APP_DATA_DIR, 'history_images', f"comp_{self.competition_data['id']}"); os.makedirs(image_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f"); shooter = self.competition_data['participants'][self.current_shooter_index]
            image_path = os.path.join(image_dir, f"shot_{shooter['id']}_{ts}.jpg")
            
            metadata = {'id': shooter['id']}
            self.request_processing.emit(frame_resized, image_path, 'competition', metadata)

    def _update_scoreboard(self, shot_number, score):
        if 1 <= shot_number <= 10:
            target_labels = [self.gui.target_1_score_label, self.gui.target_2_score_label, self.gui.target_3_score_label, self.gui.target_4_score_label]
            for label in target_labels: label.setText(f"Phát {shot_number}: {score}")
        
        total_score = sum(self.competition_data['participants'][self.current_shooter_index]['shots'])
        self.gui.total_score_label.setText(f"Tổng điểm: {total_score}")
        self.gui.ammo_count_label.setText(f"Số đạn còn lại: {10 - shot_number}/10")

    def _reset_scoreboard(self):
        self.gui.target_1_score_label.setText("Điểm: --"); self.gui.target_2_score_label.setText("Điểm: --")
        self.gui.target_3_score_label.setText("Điểm: --"); self.gui.target_4_score_label.setText("Điểm: --")
        self.gui.total_score_label.setText("Tổng điểm: 0"); self.gui.ammo_count_label.setText("Số đạn còn lại: 10/10")

    def start_camera(self):
        self.disconnect_camera(); num_cameras = count_available_cameras()
        if num_cameras == 0: self.disconnect_camera("Không tìm thấy camera.")
        elif num_cameras == 1: self.disconnect_camera("Vui lòng kết nối USB Camera.")
        else: self.connect_camera(self.configured_camera_index)
        
    def refresh_camera_connection(self): self.start_camera()

    def connect_camera(self, index: int):
        self.cam = Camera(index)
        if self.cam.isOpened(): self.video_timer.start(30); self.is_camera_connected = True
        else: self.disconnect_camera(f"Lỗi khi mở Camera Index {index}")

    def disconnect_camera(self, message="Vui lòng kết nối camera và nhấn 'Làm mới'"):
        self.video_timer.stop(); self.is_camera_connected = False
        if self.cam: self.cam.release(); self.cam = None
        self.gui.clear_video_feed(message)

    def _update_participant_list(self):
        self.gui.participants_list.clear()
        if not self.competition_data: return
        for idx, p in enumerate(self.competition_data['participants']):
            widget = ParticipantItemWidget(p['name'], p['class_name']); widget.set_status(p['status']); item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint()); self.gui.participants_list.addItem(item); self.gui.participants_list.setItemWidget(item, widget)
            if idx == self.current_shooter_index: self.gui.participants_list.setCurrentItem(item)

    def next_shooter(self):
        if not self.competition_data: return
        if 0 <= self.current_shooter_index < len(self.competition_data['participants']): self.competition_data['participants'][self.current_shooter_index]['status'] = 'finished'
        self.current_shooter_index += 1
        if self.current_shooter_index >= len(self.competition_data['participants']): self.end_competition(); return
        
        shooter = self.competition_data['participants'][self.current_shooter_index]; shooter['status'] = 'shooting'; self.current_shot_count = 0
        self.gui.shooter_name_label.setText(f"Tên: {shooter['name']}"); self.gui.shooter_class_label.setText(f"Đơn vị: {shooter['class_name']}")
        self._reset_scoreboard(); self._update_participant_list(); self.gui.score_stack.setCurrentIndex(0); self.trigger.deactivate()

    def start_current_turn(self): self.gui.score_stack.setCurrentIndex(1); self.trigger.activate()
    def confirm_end_competition(self):
        if QMessageBox.question(self, "Kết thúc", "Bạn có chắc muốn kết thúc cuộc thi?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes: self.back_to_menu_signal.emit()
    def end_competition(self):
        QMessageBox.information(self, "Hoàn thành", "Cuộc thi đã kết thúc!"); self.back_to_menu_signal.emit()
    def shutdown_components(self): self.trigger.deactivate(); self.disconnect_camera()
    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating; self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("HỦY" if is_calibrating else "HIỆU CHỈNH TÂM")
        if not is_calibrating: self.calibrated_center = None
    def on_camera_view_clicked(self, point: QPoint):
        if not self.gui.camera_view_label._is_calibrating: return
        pixmap = self.gui.camera_view_label.pixmap(); view_size = self.gui.camera_view_label.size()
        if not pixmap or pixmap.isNull(): return
        scaled_pixmap = pixmap.scaled(view_size, Qt.KeepAspectRatio); scaled_rect = scaled_pixmap.rect()
        scaled_rect.moveCenter(self.gui.camera_view_label.rect().center())
        if not scaled_rect.contains(point): return
        
        frame_h, frame_w = self.final_size[0], self.final_size[1]
        relative_x = (point.x() - scaled_rect.x()) / scaled_rect.width(); relative_y = (point.y() - scaled_rect.y()) / scaled_rect.height()
        self.calibrated_center = (int(relative_x * frame_w), int(relative_y * frame_h))
        logger.info(f"Hiệu chỉnh tâm thành công. Tọa độ mới: {self.calibrated_center}"); self.toggle_calibration_mode()
    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    def on_zoom_slider_changed(self, value): self.zoom_level = value / 10.0; self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")