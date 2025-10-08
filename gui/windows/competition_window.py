# file: gui/windows/competition_window.py
import logging
from datetime import datetime
import json
import os
import time
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QListWidgetItem, QWidget,
    QHBoxLayout, QVBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QPoint, QSize
from PySide6.QtGui import QFont, QPixmap
import numpy as np
import cv2

from ..ui.ui_competition import CompetitionGui
from core.worker import ProcessingWorker
from core.triggers import BluetoothTrigger
from core.database import DatabaseManager
from utils.filter import apply_gamma_correction
from utils.camera import Camera, find_available_cameras
from config import APP_DATA_DIR
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

# =================== WIDGET TÙY CHỈNH CHO ITEM (ĐÃ CẬP NHẬT) ===================
class ParticipantItemWidget(QWidget):
    """
    Widget này đại diện cho một người bắn trong danh sách thi đấu,
    bao gồm icon, tên, lớp và một nhãn trạng thái.
    """
    def __init__(self, name: str, class_name: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget { background-color: #34495e; border-radius: 8px; color: #ecf0f1; }
            QLabel { background-color: transparent; }
            #status_label { font-size: 10px; font-weight: bold; border-radius: 4px; padding: 4px 8px; }
        """)
        main_layout = QHBoxLayout(self); main_layout.setContentsMargins(10, 10, 10, 10); main_layout.setSpacing(10)
        icon_label = QLabel(); icon_label.setFixedSize(32, 32)
        icon_path = resource_path("assets/images/icon/user_icon.png")
        icon_label.setPixmap(QPixmap(icon_path)); icon_label.setScaledContents(True)
        info_layout = QVBoxLayout(); info_layout.setSpacing(2)
        name_label = QLabel(name); font_name = QFont(); font_name.setPointSize(12); font_name.setBold(True); name_label.setFont(font_name)
        class_name_label = QLabel(class_name); font_class = QFont(); font_class.setPointSize(10); class_name_label.setFont(font_class); class_name_label.setStyleSheet("color: #bdc3c7;")
        info_layout.addWidget(name_label); info_layout.addWidget(class_name_label)
        self.status_label = QLabel(); self.status_label.setObjectName("status_label"); self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(icon_label); main_layout.addLayout(info_layout, 1); main_layout.addWidget(self.status_label)
        self.set_status("pending")

    def set_status(self, status: str):
        """Cập nhật trạng thái: 'pending', 'competing', hoặc 'finished'."""
        if status == "finished":
            self.status_label.setText("ĐÃ HOÀN THÀNH")
            self.status_label.setStyleSheet("background-color: #27ae60; color: white;") # Xanh lá
        elif status == "competing":
            self.status_label.setText("ĐANG THI ĐẤU")
            self.status_label.setStyleSheet("background-color: #3498db; color: white;") # Xanh dương
        else: # 'pending'
            self.status_label.setText("CHƯA THI ĐẤU")
            self.status_label.setStyleSheet("background-color: #f39c12; color: white;") # Vàng
# =================================================================


class CompetitionWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)
    competition_finished = Signal()

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger):
        super().__init__()
        self.setWindowTitle("Màn Hình Thi Đấu")
        
        self.gui = CompetitionGui()
        self.setCentralWidget(self.gui)
        
        self.db = DatabaseManager()
        self.worker = worker
        self.bt_trigger = trigger
        
        # --- Các thuộc tính quản lý logic thi đấu ---
        self.competition_id = None
        self.participants = []
        self.current_shooter_index = -1
        self.is_turn_active = False
        self.current_shots_data = []
        self.MAX_AMMO = 12 

        # --- Các thuộc tính camera và xử lý ảnh ---
        self.cam: Camera | None = None; self.video_timer = QTimer(self)
        self.final_size = (480, 640); self.zoom_level = 1.0; self.current_gamma = 1.0
        self.calibrated_center = None; self.is_camera_connected = False
        self.frame_read_failures = 0; self.FRAME_FAILURE_THRESHOLD = 5
        self.last_clean_zoomed_frame = None; self.configured_camera_index = 0
        
        self._connect_signals()
        
        self.gui.participants_list.setStyleSheet("""
            QListWidget { background-color: #2c3e50; border: 1px solid #4a6278; }
            QListWidget::item { padding: 4px 0px; border-bottom: 1px solid #253442; }
            QListWidget::item:selected { background-color: #1abc9c; }
        """)
        
        self.load_config()

    def _connect_signals(self):
        self.worker.finished.connect(self.handle_processing_result)
        self.bt_trigger.triggered.connect(self.handle_shot)
        
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.gamma_slider.valueChanged.connect(self.on_gamma_slider_changed)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        
        self.gui.start_turn_button.clicked.connect(self.start_current_turn)
        self.gui.back_button.clicked.connect(self._handle_exit_request)

    # =================== LOGIC QUẢN LÝ THI ĐẤU ===================

    def setup_competition(self, competition_id: int, participants: list):
        self.competition_id = competition_id
        self.participants = participants
        self.current_shooter_index = -1
        self.is_turn_active = False
        
        logger.info(f"Đã thiết lập cho cuộc thi ID: {self.competition_id} với {len(self.participants)} xạ thủ.")
        
        self.gui.participants_list.clear()
        for shooter in self.participants:
            widget = ParticipantItemWidget(name=shooter['name'], class_name=shooter['class_name'])
            item = QListWidgetItem(self.gui.participants_list)
            item.setSizeHint(widget.sizeHint())
            item.setData(Qt.UserRole, shooter['id'])
            self.gui.participants_list.addItem(item)
            self.gui.participants_list.setItemWidget(item, widget)
            
        self.prepare_next_turn()

    def prepare_next_turn(self):
        self.current_shooter_index += 1
        
        if self.current_shooter_index < len(self.participants):
            self.gui.participants_list.setCurrentRow(self.current_shooter_index)
            self.gui.score_stack.setCurrentIndex(0) 
        else:
            self.finish_competition()

    @Slot()
    def start_current_turn(self):
        """Bắt đầu lượt bắn cho xạ thủ hiện tại."""
        if self.current_shooter_index >= len(self.participants):
            logger.warning("Lỗi: Cố gắng bắt đầu lượt khi đã hết xạ thủ.")
            return

        shooter_info = self.participants[self.current_shooter_index]
        logger.info(f"Bắt đầu lượt của xạ thủ: {shooter_info['name']} (ID: {shooter_info['id']})")

        # === CẬP NHẬT TRẠNG THÁI THÀNH "ĐANG THI ĐẤU" ===
        item = self.gui.participants_list.item(self.current_shooter_index)
        widget = self.gui.participants_list.itemWidget(item)
        if widget:
            widget.set_status("competing")
        # ===============================================

        self.is_turn_active = True
        self.current_shots_data = []

        self.gui.score_stack.setCurrentIndex(1)
        self.gui.shooter_name_label.setText(f"Tên: {shooter_info['name']}")
        self.gui.shooter_class_label.setText(f"Đơn vị: {shooter_info['class_name']}")
        self._update_scoreboard()

    def end_current_turn(self):
        self.is_turn_active = False
        shooter_info = self.participants[self.current_shooter_index]
        logger.info(f"Kết thúc lượt của xạ thủ: {shooter_info['name']}.")

        item = self.gui.participants_list.item(self.current_shooter_index)
        widget = self.gui.participants_list.itemWidget(item)
        if widget:
            widget.set_status("finished")

        QTimer.singleShot(2000, self.prepare_next_turn)

    def finish_competition(self):
        logger.info(f"Cuộc thi ID: {self.competition_id} đã hoàn thành.")
        QMessageBox.information(self, "Hoàn thành", "Cuộc thi đã kết thúc!")
        
        self.shutdown_components()
        self.competition_finished.emit()

    # =================== LOGIC XỬ LÝ BẮN ===================

    @Slot()
    def handle_shot(self):
        if not self.is_turn_active:
            logger.warning("Nhận được trigger nhưng lượt bắn chưa active.")
            return
        
        if not self.is_camera_connected or self.last_clean_zoomed_frame is None:
            logger.error("Không thể xử lý phát bắn: Camera chưa sẵn sàng.")
            return

        logger.info("Phát hiện phát bắn! Gửi yêu cầu xử lý...")
        
        shooter_id = self.participants[self.current_shooter_index]['id']
        context = {
            'type': 'competition',
            'competition_id': self.competition_id,
            'shooter_id': shooter_id
        }
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        image_name = f"shot_{self.competition_id}_{shooter_id}_{timestamp}.jpg"
        image_path = os.path.join(APP_DATA_DIR, "shots", image_name)
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        
        self.request_processing.emit(self.last_clean_zoomed_frame.copy(), context, image_path)
        self.is_turn_active = False

    @Slot(dict)
    def handle_processing_result(self, result: dict):
        context = result.get('context', {})
        if context.get('type') != 'competition' or context.get('competition_id') != self.competition_id:
            return

        logger.info(f"Nhận kết quả cho xạ thủ ID {context.get('shooter_id')}: Điểm = {result.get('score')}")
        
        shot_id = self.db.add_competition_shot(
            competition_id=self.competition_id,
            shooter_id=context['shooter_id'],
            score=result.get('score', 0),
            coords=json.dumps(result.get('coords')),
            image_path=result.get('image_path'),
            target_name=result.get('target_name')
        )
        if not shot_id:
            logger.error("LỖI NGHIÊM TRỌNG: Không thể lưu phát bắn vào database.")

        self.current_shots_data.append(result)
        self._update_scoreboard()

        if len(self.current_shots_data) >= self.MAX_AMMO:
            self.end_current_turn()
        else:
            self.is_turn_active = True
            
    def _update_scoreboard(self):
        total_score = 0
        ammo_shot = len(self.current_shots_data)
        
        labels = [
            self.gui.target_1_score_label, self.gui.target_2_score_label,
            self.gui.target_3_score_label, self.gui.target_4_score_label
        ]
        for label in labels:
            label.setText("Điểm: --")

        for i, shot_data in enumerate(self.current_shots_data):
            score = shot_data.get('score', 0)
            total_score += score
            if i < len(labels):
                labels[i].setText(f"Điểm: {score}")

        self.gui.total_score_label.setText(f"Tổng điểm: {total_score}")
        self.gui.ammo_count_label.setText(f"Số đạn còn lại: {self.MAX_AMMO - ammo_shot}/{self.MAX_AMMO}")

    # =================== QUẢN LÝ CỬA SỔ VÀ CAMERA ===================

    def start_camera(self):
        logger.info("Màn hình thi đấu: Kích hoạt camera...")
        if self.cam is None or not self.cam.isOpened():
            self.refresh_camera_connection()

    def shutdown_components(self):
        logger.info("COMPETITION: Dọn dẹp tài nguyên...")
        self.disconnect_camera()
        if self.bt_trigger: self.bt_trigger.deactivate()

    @Slot()
    def _handle_exit_request(self):
        if self.is_turn_active:
            reply = QMessageBox.warning(
                self, "Xác nhận Thoát",
                "Lượt bắn đang diễn ra. Bạn có chắc chắn muốn thoát?\nToàn bộ tiến trình của cuộc thi sẽ bị hủy.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        logger.info("Người dùng yêu cầu thoát khỏi màn hình thi đấu.")
        self.shutdown_components()
        self.competition_finished.emit()

    # --- CÁC HÀM XỬ LÝ CAMERA, ZOOM, GAMMA... (GIỮ NGUYÊN) ---
    @Slot(int)
    def on_gamma_slider_changed(self, value):
        self.current_gamma = value / 10.0
        self.gui.gamma_value_label.setText(f"{self.current_gamma:.1f}")
    @Slot(int)
    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0
        self.gui.zoom_value_label.setText(f"{self.zoom_level:.1f}x")
    def update_frame(self):
        if not (self.cam and self.cam.isOpened()): return
        ret, frame = self.cam.read()
        if not ret or frame is None:
            self.frame_read_failures += 1
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD: self.disconnect_camera("Mất kết nối với camera...")
            return
        self.frame_read_failures = 0
        if not self.is_camera_connected: self.is_camera_connected = True
        processed_frame = self.crop_and_resize_frame(frame)
        filtered_frame = apply_gamma_correction(processed_frame, gamma=self.current_gamma)
        zoomed_frame = self.apply_digital_zoom(filtered_frame, self.zoom_level)
        self.last_clean_zoomed_frame = zoomed_frame
        frame_to_display = zoomed_frame.copy()
        point_to_draw = None
        if self.calibrated_center:
            cx, cy = self.calibrated_center; h, w, _ = processed_frame.shape
            start_x = (w - int(w / self.zoom_level)) // 2; start_y = (h - int(h / self.zoom_level)) // 2
            if cx >= start_x and cy >= start_y:
                zoomed_cx = int((cx - start_x) * self.zoom_level); zoomed_cy = int((cy - start_y) * self.zoom_level)
                if zoomed_cx < w and zoomed_cy < h: point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            h_zoom, w_zoom, _ = frame_to_display.shape; point_to_draw = (w_zoom // 2, h_zoom // 2)
        if point_to_draw: cv2.drawMarker(frame_to_display, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
        self.gui.display_frame(frame_to_display)
    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape; target_aspect_ratio = 3.0 / 4.0; new_w = int(h * target_aspect_ratio)
        start_x = (w - new_w) // 2 if w > new_w else 0; cropped_frame = frame[:, start_x : start_x + new_w]
        return cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)
    def apply_digital_zoom(self, frame, zoom):
        if zoom <= 1.0: return frame
        h, w, _ = frame.shape; crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
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
        click_on_display_x = click_pos.x() - offset_x; click_on_display_y = click_pos.y() - offset_y
        click_on_zoomed_image_x = int(click_on_display_x / scale); click_on_zoomed_image_y = int(click_on_display_y / scale)
        start_x_on_original = (img_w - int(img_w / self.zoom_level)) // 2; start_y_on_original = (img_h - int(img_h / self.zoom_level)) // 2
        final_img_x = int(start_x_on_original + (click_on_zoomed_image_x / self.zoom_level)); final_img_y = int(start_y_on_original + (click_on_zoomed_image_y / self.zoom_level))
        self.calibrated_center = (final_img_x, final_img_y)
        logger.info(f"Đã cập nhật tâm ngắm mới tại: {self.calibrated_center}"); self.toggle_calibration_mode()
    def connect_camera(self, index):
        self.disconnect_camera(); self.cam = Camera(index)
        if not self.cam.isOpened(): self.disconnect_camera(f"Lỗi: Không thể mở Camera {index}"); return
        is_frame_read_successfully = False
        for _ in range(10):
            ret, frame = self.cam.read()
            if ret and frame is not None: is_frame_read_successfully = True; break
            time.sleep(0.1)
        if is_frame_read_successfully: self.video_timer.start(30); logger.info(f"COMPETITION: Kết nối thành công camera index {index}.")
        else: self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")
    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None; self.is_camera_connected = False
        self.gui.clear_video_feed(message); logger.info(f"Đã ngắt kết nối camera. Lý do: {message}")
    def refresh_camera_connection(self):
        logger.info("COMPETITION: Bắt đầu làm mới kết nối camera...")
        all_cameras = find_available_cameras()
        if len(all_cameras) > 1:
            target_index = self.configured_camera_index
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera USB tại chỉ số {target_index}.")
            self.connect_camera(target_index)
        elif len(all_cameras) == 1:
            logger.warning("Chỉ phát hiện 1 camera (laptop). Yêu cầu kết nối camera USB.")
            self.disconnect_camera(message="Vui lòng kết nối USB Camera")
        else:
            logger.warning("Không tìm thấy camera nào."); self.disconnect_camera(message="Không tìm thấy camera")
    def load_config(self):
        config_path = os.path.join(APP_DATA_DIR, "config.json")
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding='utf-8') as f:
                    config = json.load(f); self.configured_camera_index = int(config.get("camera_index", 0))
                    logger.info(f"Đã đọc cấu hình camera index = {self.configured_camera_index}")
        except Exception as e:
            logger.error(f"Lỗi khi đọc file config trong CompetitionWindow: {e}"); self.configured_camera_index = 0