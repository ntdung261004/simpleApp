# file: gui/windows/competition_window.py
import logging
from datetime import datetime
import json
import os
from PySide6.QtWidgets import (
    QMainWindow, QListWidgetItem, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QMessageBox, QDialog, QPushButton, QDialogButtonBox, QGridLayout, QFrame,
    QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView, QGroupBox
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint
from PySide6.QtGui import QPixmap, QFont, QColor, QImage
import numpy as np
import cv2
from typing import Optional

from ..ui.ui_competition import CompetitionGui, SquareImageLabel
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from core.database import DatabaseManager
from utils.audio import AudioManager
from utils.filter import apply_gamma_correction
from utils.camera import Camera, count_available_cameras
from config import APP_DATA_DIR
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class TurnResultDialog(QDialog):
    def __init__(self, shooter_name: str, scores: list, target_pixmaps: list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kết quả Lượt bắn")
        self.setMinimumWidth(600)
        self.setStyleSheet("""
            QDialog { background-color: #34495e; }
            QLabel { color: #ecf0f1; font-size: 14px; }
            QLabel#title { font-size: 18px; font-weight: bold; }
            QLabel#total_score { font-size: 24px; font-weight: bold; color: #f1c40f; }
            QGroupBox { font-size: 14px; font-weight: bold; border: 1px solid #4a6278; border-radius: 8px; margin-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top center; padding: 2px 8px; }
            QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 8px 18px; border-radius: 8px; }
            QPushButton:hover { background-color: #16a085; }
            QPushButton[objectName="retryButton"] { background-color: #e67e22; }
            QPushButton[objectName="retryButton"]:hover { background-color: #d35400; }
        """)
        main_layout = QVBoxLayout(self); main_layout.setSpacing(15); title_label = QLabel(f"Kết quả của: {shooter_name}"); title_label.setObjectName("title"); title_label.setAlignment(Qt.AlignCenter); main_layout.addWidget(title_label); summary_layout = QHBoxLayout(); summary_layout.setAlignment(Qt.AlignCenter); summary_label = QLabel("Tổng điểm:"); summary_layout.addWidget(summary_label); total_score_label = QLabel(str(sum(scores))); total_score_label.setObjectName("total_score"); summary_layout.addWidget(total_score_label); main_layout.addLayout(summary_layout); targets_image_box = QGroupBox("Ảnh bia Thực tế"); targets_image_layout = QHBoxLayout(targets_image_box); targets_image_layout.setSpacing(10)
        for i, pixmap in enumerate(target_pixmaps):
            target_widget = QWidget(); target_layout = QVBoxLayout(target_widget); img_label = QLabel(); img_label.setPixmap(pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)); img_label.setAlignment(Qt.AlignCenter); bia_label = QLabel(f"Bia {i+1}"); bia_label.setAlignment(Qt.AlignCenter); target_layout.addWidget(img_label); target_layout.addWidget(bia_label); targets_image_layout.addWidget(target_widget)
        main_layout.addWidget(targets_image_box); separator = QFrame(); separator.setFrameShape(QFrame.HLine); separator.setFrameShadow(QFrame.Sunken); main_layout.addWidget(separator); details_box = QGroupBox("Chi tiết điểm số"); details_layout = QGridLayout(details_box); targets_scores = [scores[i:i + 3] for i in range(0, len(scores), 3)]
        for i, target_shots in enumerate(targets_scores): target_label = QLabel(f"<b>Bia số {i+1}:</b>"); details_layout.addWidget(target_label, i, 0); scores_text = " - ".join(map(str, target_shots)); details_layout.addWidget(QLabel(scores_text), i, 1); total_label = QLabel(f"<b>Tổng: {sum(target_shots)}</b>"); total_label.setAlignment(Qt.AlignRight); details_layout.addWidget(total_label, i, 2)
        main_layout.addWidget(details_box); buttons = QDialogButtonBox(); save_button = buttons.addButton("Lưu & Tiếp tục", QDialogButtonBox.AcceptRole); retry_button = buttons.addButton("Bắn lại", QDialogButtonBox.RejectRole); retry_button.setObjectName("retryButton"); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); main_layout.addWidget(buttons)

class CompetitionRankingDialog(QDialog):
    def __init__(self, competition_id: int, competition_name: str, participants_data: list, db: DatabaseManager, parent=None):
        super().__init__(parent); self.competition_id = competition_id; self.db = db; self.setWindowTitle("Bảng Xếp Hạng Chung Cuộc"); self.setMinimumSize(600, 500)
        self.setStyleSheet(""" QDialog { background-color: #2c3e50; } QLabel#title { font-size: 22px; font-weight: bold; color: #1abc9c; padding-bottom: 10px; } QTableWidget { background-color: #34495e; border: 1px solid #4a6278; gridline-color: #4a6278; font-size: 14px; } QHeaderView::section { background-color: #415a72; color: white; padding: 8px; font-weight: bold; border: none; } QTableWidget::item { padding: 10px; border-bottom: 1px solid #4a6278; } QPushButton { background-color: #1abc9c; color: white; font-size: 14px; font-weight: bold; border: none; padding: 10px 20px; border-radius: 8px; } QPushButton:hover { background-color: #16a085; } QPushButton[objectName="exitButton"] { background-color: #e74c3c; } QPushButton[objectName="exitButton"]:hover { background-color: #c0392b; } """)
        main_layout = QVBoxLayout(self); main_layout.setSpacing(15); title = QLabel(f"Kết quả: {competition_name}"); title.setObjectName("title"); title.setAlignment(Qt.AlignCenter); main_layout.addWidget(title); self.table = QTableWidget(); self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["Hạng", "Tên Xạ thủ", "Đơn vị", "Tổng Điểm"]); self.table.verticalHeader().setVisible(False); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents); main_layout.addWidget(self.table); sorted_participants = sorted(participants_data, key=lambda p: sum(p.get('shots', [])), reverse=True); self._populate_table(sorted_participants); buttons = QDialogButtonBox(); save_button = QPushButton("Lưu & Thoát"); exit_button = QPushButton("Thoát không lưu"); exit_button.setObjectName("exitButton"); buttons.addButton(save_button, QDialogButtonBox.AcceptRole); buttons.addButton(exit_button, QDialogButtonBox.RejectRole); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); main_layout.addWidget(buttons)
    def accept(self): logger.info(f"Người dùng chọn LƯU kết quả cuộc thi ID: {self.competition_id}"); self.db.update_competition_status(self.competition_id, 'completed'); super().accept()
    def reject(self): logger.info(f"Người dùng chọn KHÔNG LƯU kết quả cuộc thi ID: {self.competition_id}. Dữ liệu sẽ bị xóa."); self.db.delete_competition(self.competition_id); super().reject()
    def _populate_table(self, participants):
        rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
        for i, p in enumerate(participants):
            rank = i + 1; self.table.insertRow(i); rank_text = rank_icons.get(rank, f"{rank}"); rank_item = QTableWidgetItem(rank_text); rank_item.setTextAlignment(Qt.AlignCenter)
            if rank <= 3: rank_item.setFont(QFont("Segoe UI", 16))
            self.table.setItem(i, 0, rank_item); self.table.setItem(i, 1, QTableWidgetItem(p['name'])); self.table.setItem(i, 2, QTableWidgetItem(p['class_name'])); total_score = sum(p.get('shots', [])); score_item = QTableWidgetItem(str(total_score)); score_item.setTextAlignment(Qt.AlignCenter); score_item.setFont(QFont("Segoe UI", 14, QFont.Bold)); score_item.setForeground(QColor("#f1c40f")); self.table.setItem(i, 3, score_item)

class ParticipantItemWidget(QWidget):
    def __init__(self, name: str, class_name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 8px; }
            QLabel { color: white; background-color: transparent; border: none; }
            #status_label { font-size: 11px; font-weight: bold; padding: 3px 10px; border-radius: 5px; }
        """)
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)
        icon_label.setPixmap(QPixmap(resource_path("assets/images/icon/user_icon.png")))
        icon_label.setScaledContents(True)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        name_label = QLabel(f"<b>{name}</b>")
        class_label = QLabel(class_name)
        class_label.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(name_label)
        info_layout.addWidget(class_label)
        self.status_label = QLabel("Chưa bắn")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label)
        main_layout.addLayout(info_layout, 1)
        main_layout.addWidget(self.status_label)

    def set_status(self, status: str):
        text, color, text_color = {"waiting": ("CHỜ", "#7f8c8d", "white"), "shooting": ("ĐANG BẮN", "#f39c12", "#2c3e50"), "finished": ("HOÀN THÀNH", "#27ae60", "white")}.get(status, ("LỖI", "#c0392b", "white"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"background-color: {color}; color: {text_color}; font-size: 11px; font-weight: bold; padding: 3px 10px; border-radius: 5px;")

class CompetitionWindow(QMainWindow):
    request_processing = Signal(np.ndarray, str, str, object)
    back_to_menu_signal = Signal()
    TOTAL_SHOTS = 12
    TARGET_DIMENSIONS = {'bia_4b': (500, 500), 'bia_4c': (500, 500)}

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger, config: dict):
        super().__init__()
        self.gui = CompetitionGui()
        self.setCentralWidget(self.gui)
        self.setStyleSheet("background-color: #2c3e50;")
        self.setWindowTitle("Chế Độ Kiểm Tra")
        self.configured_camera_index = config.get('camera_index', 0)
        self.db = DatabaseManager()
        self.trigger = trigger
        self.worker = worker
        self.audio_manager = AudioManager()
        self.cam = None
        self.final_size = (640, 480)
        self.zoom_level = 1.0
        self.current_gamma = 1.0
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_frame)
        self.competition_data = None
        self.current_shooter_index = -1
        self.current_shot_count = 0
        self.is_camera_connected = False
        self.calibrated_center = None
        self.is_shot_processing = False

        self.target_image_labels = {
            1: self.gui.target_1_image_label,
            2: self.gui.target_2_image_label,
            3: self.gui.target_3_image_label,
            4: self.gui.target_4_image_label
        }
        self.target_score_labels = {
            1: self.gui.target_1_score_label,
            2: self.gui.target_2_score_label,
            3: self.gui.target_3_score_label,
            4: self.gui.target_4_score_label,
        }
        self._setup_connections()

    def _setup_connections(self):
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_slider_changed)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.camera_view_label.clicked.connect(self.on_camera_view_clicked)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.start_turn_button.clicked.connect(self.start_current_turn)
        self.gui.participants_list.itemClicked.connect(self.on_participant_selected)
        self.gui.back_button.clicked.connect(self._prompt_exit)
        self.gui.save_button.clicked.connect(self._save_competition_state)

    def _crop_frame_to_3_4(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        new_w = int(h * 3.0 / 4.0)
        if new_w > w: return frame
        start_x = (w - new_w) // 2
        return frame[:, start_x : start_x + new_w]

    def _apply_effects_to_frame(self, frame: np.ndarray) -> np.ndarray:
        processed_frame = frame.copy()
        if self.current_gamma != 1.0: processed_frame = apply_gamma_correction(processed_frame, self.current_gamma)
        if self.zoom_level > 1.0:
            h, w, _ = processed_frame.shape
            new_w, new_h = int(w / self.zoom_level), int(h / self.zoom_level)
            start_x, start_y = (w - new_w) // 2, (h - new_h) // 2
            processed_frame = processed_frame[start_y : start_y + new_h, start_x : start_x + new_w]
            processed_frame = cv2.resize(processed_frame, (w, h))
        return processed_frame

    def update_frame(self):
        if not self.is_camera_connected or self.cam is None: return
        ret, frame = self.cam.read()
        if not ret: self.disconnect_camera("Mất kết nối camera\nVui lòng kết nối lại và nhấn làm mới."); return
        frame_resized = cv2.resize(self._crop_frame_to_3_4(frame), (self.final_size[1], self.final_size[0]))
        frame_with_effects = self._apply_effects_to_frame(frame_resized)
        h, w, _ = frame_resized.shape
        original_aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
        display_aim_point = original_aim_point
        if self.zoom_level > 1.0:
            zoomed_w, zoomed_h = int(w / self.zoom_level), int(h / self.zoom_level)
            crop_start_x, crop_start_y = (w - zoomed_w) // 2, (h - zoomed_h) // 2
            transformed_x = original_aim_point[0] - crop_start_x
            transformed_y = original_aim_point[1] - crop_start_y
            display_aim_point = (int(transformed_x * self.zoom_level), int(transformed_y * self.zoom_level))
        cv2.drawMarker(frame_with_effects, display_aim_point, (0, 0, 255), cv2.MARKER_CROSS, 20, 2)
        self.gui.display_frame(frame_with_effects)

    def setup_competition(self, competition_id: int, competition_name: str, participants: list):
        logger.info(f"Bắt đầu thiết lập kiểm tra MỚI: '{competition_name}' (ID: {competition_id})")
        self._reset_state(); self.setWindowTitle(f"Kiểm tra - {competition_name}"); self.competition_data = {'id': competition_id, 'name': competition_name, 'participants': [{'id': p['id'], 'name': p['name'], 'class_name': p['class_name'], 'shots': [], 'status': 'waiting'} for p in participants]}; self._update_participant_list(); self.gui.participants_list.setEnabled(True)

    def load_from_state(self, state_data: dict):
        try:
            logger.info(f"Bắt đầu khôi phục kiểm tra đã lưu ID: {state_data.get('competition_id')}")
            self._reset_state(); competition_info = self.db.get_competition(state_data['competition_id'])
            if not competition_info: raise ValueError("Không tìm thấy ID kiểm tra trong database.")
            self.competition_data = {'id': state_data['competition_id'], 'name': competition_info['name'], 'participants': state_data['participants']}; self.current_shooter_index = state_data['current_shooter_index']; self.current_shot_count = state_data['current_shot_count']; self.setWindowTitle(f"Kiểm tra - {self.competition_data['name']}"); self._update_participant_list()
            is_shooting = (self.current_shooter_index != -1 and self.competition_data['participants'][self.current_shooter_index]['status'] == 'shooting')
            if is_shooting: self.gui.score_stack.setCurrentIndex(1); self.gui.participants_list.setEnabled(False); self.gui.start_turn_button.setEnabled(False); self._rebuild_scoreboard()
            else: self.gui.score_stack.setCurrentIndex(0); self.gui.participants_list.setEnabled(True); self.gui.start_turn_button.setEnabled(False)
        except (KeyError, IndexError, TypeError, ValueError) as e: logger.error(f"Lỗi nghiêm trọng khi khôi phục trạng thái: {e}"); QMessageBox.critical(self, "Lỗi Dữ liệu", "Không thể khôi phục phiên kiểm tra từ dữ liệu đã lưu."); self._reset_state(); self.back_to_menu_signal.emit()

    def _rebuild_scoreboard(self):
        self._reset_scoreboard_texts()
        if self.current_shooter_index == -1: return
        shooter = self.competition_data['participants'][self.current_shooter_index]
        self.gui.shooter_name_label.setText(f"Tên: {shooter['name']}")
        self.gui.shooter_class_label.setText(f"Đơn vị: {shooter['class_name']}")
        
        self._update_scoreboard_scores()
        
        for i in range(1, 5):
            self._redraw_target_with_shots(i)

    @Slot(dict, object)
    def handle_processing_result(self, result: dict, shooter_data: dict):
        current_shooter = self.competition_data['participants'][self.current_shooter_index]
        if not self.competition_data or shooter_data['id'] != current_shooter['id']:
            self.is_shot_processing = False
            return
            
        self.current_shot_count += 1
        score = result.get('score', 0)
        
        if score == 0: self.audio_manager.play_sound('miss')
        else: self.audio_manager.play_score(score)

        current_shooter['shots'].append(score)
        
        self.db.add_competition_shot(
            competition_id=self.competition_data['id'],
            soldier_id=shooter_data['id'],
            score=score,
            coords=result.get('coords'),
            image_path=result.get('image_path'),
            target_name=result.get('target_detected_raw', 'N/A')
        )

        self._update_scoreboard_scores()
        target_index = ((self.current_shot_count - 1) // 3) + 1
        self._redraw_target_with_shots(target_index)
        
        if self.current_shot_count >= self.TOTAL_SHOTS:
            self.show_turn_result_popup()
        else:
            self.is_shot_processing = False

    @Slot()
    def handle_shot(self):
        if not self.is_camera_connected or self.current_shot_count >= self.TOTAL_SHOTS or not self.trigger.is_active or self.is_shot_processing:
            return
        
        self.is_shot_processing = True
        
        ret, frame = self.cam.read()
        if ret and frame is not None:
            frame_resized = cv2.resize(self._crop_frame_to_3_4(frame), (self.final_size[1], self.final_size[0]))
            frame_to_send = self._apply_effects_to_frame(frame_resized)
            h, w, _ = frame_resized.shape
            original_aim_point = self.calibrated_center if self.calibrated_center else (w // 2, h // 2)
            final_aim_point = original_aim_point
            if self.zoom_level > 1.0:
                zoomed_w, zoomed_h = int(w / self.zoom_level), int(h / self.zoom_level)
                crop_start_x, crop_start_y = (w - zoomed_w) // 2, (h - zoomed_h) // 2
                final_aim_point = (int((original_aim_point[0] - crop_start_x) * self.zoom_level), int((original_aim_point[1] - crop_start_y) * self.zoom_level))
            image_dir = os.path.join(APP_DATA_DIR, 'history_images', f"comp_{self.competition_data['id']}")
            os.makedirs(image_dir, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            shooter = self.competition_data['participants'][self.current_shooter_index]
            image_path = os.path.join(image_dir, f"shot_{shooter['id']}_{ts}.jpg")
            metadata = {'id': shooter['id'], 'aim_point': final_aim_point}
            
            self.request_processing.emit(frame_to_send, image_path, 'competition', metadata)
            self.audio_manager.play_sound('shot')
        else:
            self.is_shot_processing = False

    def _redraw_target_with_shots(self, target_index: int):
        # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
        logger.info(f"--- Bắt đầu vẽ lại bia số {target_index} ---")
        # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===
        if not (1 <= target_index <= 4) or not self.competition_data or self.current_shooter_index == -1:
            return

        target_image_label = self.target_image_labels.get(target_index)
        if not target_image_label:
            return

        target_type = 'bia_4b' if target_index <= 2 else 'bia_4c'
        image_path = resource_path(f"assets/images/original/{target_type}.png")
        
        # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
        logger.info(f"Đang tải ảnh bia gốc từ đường dẫn: '{image_path}'")
        # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===
        
        base_image = cv2.imread(image_path)
        if base_image is None:
            logger.error(f"Lỗi nghiêm trọng: Không thể tải ảnh bia gốc tại {image_path}. Hàm sẽ dừng lại.")
            target_image_label.setPixmap(QPixmap())
            return
        
        shooter_id = self.competition_data['participants'][self.current_shooter_index]['id']
        all_shots_from_db = self.db.get_shots_for_competition(self.competition_data['id'], shooter_id)

        start_shot_num = ((target_index - 1) * 3) + 1
        end_shot_num = start_shot_num + 2
        relevant_shots = [s for s in all_shots_from_db if start_shot_num <= s.get('shot_number', 0) <= end_shot_num]

        # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
        logger.info(f"Tìm thấy {len(relevant_shots)} phát bắn hợp lệ cho bia này (từ phát {start_shot_num} đến {end_shot_num}).")
        # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===

        for shot in relevant_shots:
            coords_str = shot.get('coords')
            if not coords_str:
                continue
            try:
                coords = json.loads(coords_str)
                if coords and isinstance(coords, list) and len(coords) == 2:
                    draw_point = (int(coords[0]), int(coords[1]))
                    # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
                    logger.info(f"  -> Đang vẽ vết đạn cho phát bắn số {shot.get('shot_number')} tại tọa độ {draw_point}")
                    # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===
                    cv2.drawMarker(base_image, draw_point, (0, 0, 255), cv2.MARKER_CROSS, 40, 3)
            except (json.JSONDecodeError, TypeError):
                # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
                logger.warning(f"Bỏ qua vẽ vết đạn cho phát bắn ID {shot.get('id')} do lỗi parse tọa độ: '{coords_str}'")
                # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===

        rgb_image = cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QPixmap.fromImage(QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888))
        target_image_label.setPixmap(qt_image)
        # === BẮT ĐẦU VÙNG LOGGING BỔ SUNG ===
        logger.info(f"--- Hoàn tất vẽ lại bia số {target_index} ---")
        # === KẾT THÚC VÙNG LOGGING BỔ SUNG ===

    def _update_scoreboard_scores(self):
        if not self.competition_data or self.current_shooter_index == -1:
            return
        
        shooter = self.competition_data['participants'][self.current_shooter_index]
        all_scores = shooter.get('shots', [])

        for i in range(1, 5):
            score_label = self.target_score_labels.get(i)
            if not score_label: continue

            start_index = (i - 1) * 3
            target_scores = all_scores[start_index : start_index + 3]
            
            if not target_scores:
                score_label.setText("Điểm: --")
            else:
                score_text = " - ".join(map(str, target_scores))
                score_label.setText(f"Điểm: {score_text}")

        total_score = sum(all_scores)
        self.gui.total_score_label.setText(f"Tổng điểm: {total_score}")
        self.gui.ammo_count_label.setText(f"Số đạn còn lại: {self.TOTAL_SHOTS - len(all_scores)}/{self.TOTAL_SHOTS}")

    def _reset_scoreboard_texts(self):
        for i in range(1, 5):
            self.target_score_labels[i].setText("Điểm: --")
        self.gui.total_score_label.setText("Tổng điểm: 0")
        self.gui.ammo_count_label.setText(f"Số đạn còn lại: {self.TOTAL_SHOTS}/{self.TOTAL_SHOTS}")

    def start_camera(self):
        self.disconnect_camera()
        num_cameras = count_available_cameras()
        if num_cameras < 2: self.disconnect_camera("Vui lòng kết nối USB camera và nhấn 'Làm mới'")
        else:
            if self.configured_camera_index < num_cameras: self.connect_camera(self.configured_camera_index)
            else: self.disconnect_camera(f"Lỗi: Index ({self.configured_camera_index}) không hợp lệ. Tìm thấy {num_cameras} camera.")

    def refresh_camera_connection(self): self.start_camera()

    def connect_camera(self, index: int):
        self.disconnect_camera()
        self.cam = Camera(index)
        if self.cam.isOpened():
            self.video_timer.start(30); self.is_camera_connected = True
            if self.competition_data and self.current_shooter_index != -1 and self.competition_data['participants'][self.current_shooter_index]['status'] == 'shooting':
                logger.info("Camera kết nối, kích hoạt cò súng.")
                self.trigger.activate()
        else: self.disconnect_camera(f"Lỗi khi mở Camera Index {index}")

    def disconnect_camera(self, message="Vui lòng kết nối camera và nhấn 'Làm mới'"):
        self.video_timer.stop(); self.is_camera_connected = False; self.trigger.deactivate();
        if self.cam: self.cam.release(); self.cam = None
        self.gui.clear_video_feed(message)

    def _update_participant_list(self):
        self.gui.participants_list.clear()
        if not self.competition_data: return
        for p in self.competition_data['participants']: widget = ParticipantItemWidget(p['name'], p['class_name']); widget.set_status(p['status']); item = QListWidgetItem(); item.setSizeHint(widget.sizeHint()); self.gui.participants_list.addItem(item); self.gui.participants_list.setItemWidget(item, widget)
    
    def _reset_competition_ui(self): self.gui.score_stack.setCurrentIndex(0); self.gui.start_turn_button.setEnabled(False); self.gui.shooter_name_label.setText("Tên: --"); self.gui.shooter_class_label.setText("Đơn vị: --")
    
    @Slot(QListWidgetItem)
    def on_participant_selected(self, item):
        row = self.gui.participants_list.row(item)
        if not self.competition_data or not (0 <= row < len(self.competition_data['participants'])): return
        shooter = self.competition_data['participants'][row]; self.gui.shooter_name_label.setText(f"Tên: {shooter['name']}"); self.gui.shooter_class_label.setText(f"Đơn vị: {shooter['class_name']}")
        if shooter['status'] == 'waiting': self.current_shooter_index = row; self.gui.start_turn_button.setEnabled(True)
        else: self.gui.start_turn_button.setEnabled(False)

    def start_current_turn(self):
        if self.current_shooter_index == -1: return
        shooter = self.competition_data['participants'][self.current_shooter_index]
        if shooter['status'] != 'waiting': return
        shooter['status'] = 'shooting'; self.current_shot_count = 0; self._update_participant_list(); self.gui.participants_list.setEnabled(False); self.gui.start_turn_button.setEnabled(False); self.gui.score_stack.setCurrentIndex(1)
        
        self._reset_scoreboard_texts()
        for i in range(1, 5):
            self._redraw_target_with_shots(i)
        
        self.trigger.activate()

    def show_turn_result_popup(self):
        self.trigger.deactivate()
        self.is_shot_processing = False
        shooter = self.competition_data['participants'][self.current_shooter_index]
        
        target_pixmaps = [self.target_image_labels[i]._pixmap for i in range(1, 5)]
        
        dialog = TurnResultDialog(shooter['name'], shooter['shots'], target_pixmaps, self)
        result = dialog.exec()
        if result == QDialog.Accepted: self.finalize_turn()
        else: self.retry_turn()

    def finalize_turn(self):
        if 0 <= self.current_shooter_index < len(self.competition_data['participants']):
            self.competition_data['participants'][self.current_shooter_index]['status'] = 'finished'
        if all(p['status'] == 'finished' for p in self.competition_data['participants']):
            self.end_competition()
        else:
            self._update_participant_list(); self.gui.participants_list.setEnabled(True); self.gui.participants_list.setCurrentRow(-1); self.gui.score_stack.setCurrentIndex(0)

    def retry_turn(self):
        shooter = self.competition_data['participants'][self.current_shooter_index]; success = self.db.delete_shots_for_turn(self.competition_data['id'], shooter['id'], self.TOTAL_SHOTS)
        if not success: QMessageBox.critical(self, "Lỗi Database", "Không thể xóa các phát bắn cũ."); self.finalize_turn(); return
        
        self.is_shot_processing = False
        shooter['shots'] = []; shooter['status'] = 'waiting'; self._update_participant_list(); self.gui.participants_list.setEnabled(True); self.gui.participants_list.setCurrentRow(self.current_shooter_index); self.on_participant_selected(self.gui.participants_list.item(self.current_shooter_index)); self.gui.score_stack.setCurrentIndex(0)

    def end_competition(self):
        if not self.competition_data: return
        dialog = CompetitionRankingDialog(competition_id=self.competition_data['id'], competition_name=self.competition_data['name'], participants_data=self.competition_data['participants'], db=self.db, parent=self); dialog.exec()
        self._reset_state(); self.back_to_menu_signal.emit()

    def shutdown_components(self): self.trigger.deactivate(); self.disconnect_camera()

    def toggle_calibration_mode(self, force_off=False):
        new_state_is_on = not self.gui.camera_view_label._is_calibrating
        if force_off: new_state_is_on = False
        self.gui.camera_view_label.set_calibration_mode(new_state_is_on); self.gui.calibrate_button.setText("HỦY" if new_state_is_on else "HIỆU CHỈNH TÂM")
        if new_state_is_on: QMessageBox.information(self, "Hiệu chỉnh", "Click vào vị trí tâm ngắm mong muốn trên màn hình.")
        elif not force_off: self.calibrated_center = None; logger.info("Người dùng đã hủy hiệu chỉnh.")

    def on_camera_view_clicked(self, point: QPoint):
        if not self.gui.camera_view_label._is_calibrating: return
        pixmap = self.gui.camera_view_label._pixmap;
        if not pixmap or pixmap.isNull(): return
        frame_h, frame_w = self.final_size; scaled_pixmap = pixmap.scaled(self.gui.camera_view_label.size(), Qt.KeepAspectRatio)
        offset_x = (self.gui.camera_view_label.width() - scaled_pixmap.width()) // 2; offset_y = (self.gui.camera_view_label.height() - scaled_pixmap.height()) // 2
        if not (offset_x <= point.x() < offset_x + scaled_pixmap.width() and offset_y <= point.y() < offset_y + scaled_pixmap.height()): return
        relative_x = (point.x() - offset_x) / scaled_pixmap.width(); relative_y = (point.y() - offset_y) / scaled_pixmap.height()
        unzoomed_crop_w = frame_w / self.zoom_level; unzoomed_crop_h = frame_h / self.zoom_level; x_in_zoomed_crop = relative_x * unzoomed_crop_w; y_in_zoomed_crop = relative_y * unzoomed_crop_h
        start_x = (frame_w - unzoomed_crop_w) / 2; start_y = (frame_h - unzoomed_crop_h) / 2
        self.calibrated_center = (int(start_x + x_in_zoomed_crop), int(start_y + y_in_zoomed_crop)); logger.info(f"Hiệu chỉnh tâm thành công. Tọa độ mới trên ảnh gốc: {self.calibrated_center}"); self.toggle_calibration_mode(force_off=True)

    def on_gamma_slider_changed(self, value): self.current_gamma = value / 10.0; self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    def on_zoom_slider_changed(self, value): self.zoom_level = value / 10.0; self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")

    def _gather_state_data(self) -> Optional[dict]:
        if not self.competition_data: return None
        return {'competition_id': self.competition_data['id'], 'current_shooter_index': self.current_shooter_index, 'current_shot_count': self.current_shot_count, 'participants': self.competition_data['participants']}

    @Slot()
    def _save_competition_state(self):
        state_data = self._gather_state_data()
        if state_data is None: QMessageBox.warning(self, "Chưa sẵn sàng", "Không có gì để lưu."); return
        try:
            state_json = json.dumps(state_data); success = self.db.save_competition_state(self.competition_data['id'], state_json)
            if success: QMessageBox.information(self, "Thành công", "Đã lưu lại tiến trình.")
            else: QMessageBox.critical(self, "Lỗi Database", "Không thể lưu trạng thái.")
        except TypeError as e: logger.error(f"Lỗi khi chuyển trạng thái sang JSON: {e}"); QMessageBox.critical(self, "Lỗi Dữ liệu", "Không thể chuyển đổi dữ liệu.")

    def _reset_state(self):
        logger.info("Dọn dẹp trạng thái cửa sổ thi đấu..."); self.competition_data = None; self.current_shooter_index = -1; self.current_shot_count = 0; self.is_shot_processing = False; self.gui.participants_list.setCurrentRow(-1); self.gui.participants_list.clear(); self._reset_competition_ui()

    def _prompt_exit(self):
        if self.competition_data is None: self._reset_state(); self.back_to_menu_signal.emit(); return
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Xác nhận Thoát")
        msg_box.setText("Bạn có muốn lưu lại tiến trình trước khi thoát không?")
        msg_box.setIcon(QMessageBox.Question)
        save_button = msg_box.addButton("Lưu và Thoát", QMessageBox.AcceptRole)
        exit_button = msg_box.addButton("Thoát không lưu", QMessageBox.DestructiveRole)
        cancel_button = msg_box.addButton("Hủy", QMessageBox.RejectRole)
        msg_box.exec()
        clicked_button = msg_box.clickedButton()
        if clicked_button == save_button:
            self._save_competition_state()
            self._reset_state()
            self.back_to_menu_signal.emit()
        elif clicked_button == exit_button:
            competition_info = self.db.get_competition(self.competition_data['id'])
            if competition_info and not competition_info.get('state'):
                logger.info(f"Cuộc thi ID {self.competition_data['id']} chưa từng được lưu. Sẽ xóa khỏi CSDL.")
                self.db.delete_competition(self.competition_data['id'])
            else:
                logger.info(f"Cuộc thi ID {self.competition_data['id']} đã được lưu trước đó. Giữ lại trạng thái đã lưu.")
            self._reset_state()
            self.back_to_menu_signal.emit()