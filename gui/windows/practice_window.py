# file: gui/windows/practice_window.py

import logging
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QInputDialog, QLineEdit, QDialog, QVBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, 
    QDialogButtonBox, QLabel, QHBoxLayout, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Signal, Slot, Qt, QSize
import cv2
import numpy as np
import os
from datetime import datetime
from PySide6.QtGui import QPixmap, QKeyEvent, QImage

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, CameraThread
from core.worker import ProcessingWorker
from core.database import DatabaseManager
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

# --- CLASS RESULT POPUP (GIỮ NGUYÊN) ---
class ResultPopup(QDialog):
    def __init__(self, shots_data, camera_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("KẾT QUẢ KIỂM TRA")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setMinimumSize(700, 650)
        self.setStyleSheet("background-color: #2c3e50; color: white;")
        
        self.shots_data = shots_data
        self.current_idx = 0
        
        layout = QVBoxLayout(self)
        
        if camera_name:
            self.lbl_cam = QLabel(camera_name)
            self.lbl_cam.setStyleSheet("font-size: 20px; font-weight: bold; color: #3498db; margin-top: 5px;")
            self.lbl_cam.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.lbl_cam)

        total_score = sum(s['score'] for s in self.shots_data)
        if total_score < 15:
            rank = "KHÔNG ĐẠT"; color = "#95a5a6"
        elif 15 <= total_score <= 18:
            rank = "ĐẠT"; color = "#f39c12"
        elif 19 <= total_score <= 23:
            rank = "KHÁ"; color = "#3498db"
        else:
            rank = "GIỎI"; color = "#2ecc71"

        header_layout = QHBoxLayout()
        self.lbl_score = QLabel(f"TỔNG ĐIỂM: {total_score}/30")
        self.lbl_score.setStyleSheet("font-size: 24px; font-weight: bold; color: #ecf0f1;")
        self.lbl_rank = QLabel(rank)
        self.lbl_rank.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {color};")
        header_layout.addWidget(self.lbl_score)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_rank)
        layout.addLayout(header_layout)
        
        self.img_label = QLabel()
        self.img_label.setAlignment(Qt.AlignCenter)
        self.img_label.setStyleSheet("background-color: #212f3d; border: 2px solid #bdc3c7; border-radius: 5px;")
        self.img_label.setMinimumSize(600, 400)
        layout.addWidget(self.img_label, 1)
        
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("<< Trước"); self.btn_prev.setMinimumHeight(40)
        self.btn_prev.clicked.connect(self.prev_image)
        self.lbl_index = QLabel("1/3"); self.lbl_index.setAlignment(Qt.AlignCenter)
        self.lbl_index.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.btn_next = QPushButton("Sau >>"); self.btn_next.setMinimumHeight(40)
        self.btn_next.clicked.connect(self.next_image)
        nav_layout.addWidget(self.btn_prev); nav_layout.addWidget(self.lbl_index); nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        btn_continue = QPushButton("TIẾP TỤC")
        btn_continue.setStyleSheet("background-color: #1abc9c; font-size: 16px; padding: 10px; font-weight: bold; border-radius: 5px; color: white;")
        btn_continue.clicked.connect(self.accept)
        layout.addWidget(btn_continue)
        
        self.update_view()

    def update_view(self):
        if not self.shots_data: return
        data = self.shots_data[self.current_idx]
        pix = QPixmap()
        if isinstance(data['image'], str) and os.path.exists(data['image']):
            pix = QPixmap(data['image'])
        elif isinstance(data['image'], QPixmap):
            pix = data['image']
            
        if not pix.isNull():
            self.img_label.setPixmap(pix.scaled(self.img_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else: self.img_label.setText("Lỗi: Không hiển thị được ảnh")
        self.lbl_index.setText(f"Phát {self.current_idx + 1}/{len(self.shots_data)}  -  Điểm: {data['score']}")
        self.btn_prev.setEnabled(self.current_idx > 0)
        self.btn_next.setEnabled(self.current_idx < len(self.shots_data) - 1)

    def prev_image(self):
        if self.current_idx > 0: self.current_idx -= 1; self.update_view()
    def next_image(self):
        if self.current_idx < len(self.shots_data) - 1: self.current_idx += 1; self.update_view()
    def resizeEvent(self, event): self.update_view(); super().resizeEvent(event)

# --- CLASS SELECT SOLDIER (GIỮ NGUYÊN) ---
class SelectSoldierDialog(QDialog):
    def __init__(self, soldiers_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn Người Tập")
        self.setMinimumSize(600, 500)
        self.setStyleSheet("QDialog { background-color: #2c3e50; color: white; } QLineEdit { padding: 8px; border-radius: 4px; border: 1px solid #7f8c8d; background: #34495e; color: white; } QTableWidget { background-color: #34495e; gridline-color: #7f8c8d; color: white; border: none; } QHeaderView::section { background-color: #2c3e50; color: white; padding: 4px; border: 1px solid #7f8c8d; } QTableWidget::item:selected { background-color: #1abc9c; color: white; }")
        self.selected_soldier = None; self.soldiers_list = soldiers_list
        layout = QVBoxLayout(self)
        self.search_box = QLineEdit(); self.search_box.setPlaceholderText("🔍 Tìm kiếm tên hoặc đơn vị...")
        self.search_box.textChanged.connect(self.filter_list); layout.addWidget(self.search_box)
        self.table = QTableWidget(); self.table.setColumnCount(2); self.table.setHorizontalHeaderLabels(["Họ Tên", "Đơn vị"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.doubleClicked.connect(self.accept_selection); layout.addWidget(self.table)
        self.populate_table(self.soldiers_list)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); btn_box.accepted.connect(self.accept_selection); btn_box.rejected.connect(self.reject); layout.addWidget(btn_box)
    def populate_table(self, data):
        self.table.setRowCount(len(data))
        for r, s in enumerate(data):
            self.table.setItem(r, 0, QTableWidgetItem(s['name'])); self.table.setItem(r, 1, QTableWidgetItem(s.get('class_name', '')))
            self.table.item(r, 0).setData(Qt.UserRole, s) 
    def filter_list(self):
        text = self.search_box.text().lower()
        for r in range(self.table.rowCount()):
            name = self.table.item(r, 0).text().lower(); unit = self.table.item(r, 1).text().lower()
            self.table.setRowHidden(r, text not in name and text not in unit)
    def accept_selection(self):
        rows = self.table.selectedItems()
        if rows: self.selected_soldier = self.table.item(rows[0].row(), 0).data(Qt.UserRole); self.accept()
        else: QMessageBox.warning(self, "Chưa chọn", "Vui lòng chọn một người từ danh sách.")

# --- PRACTICE WINDOW CHÍNH ---
class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self, worker: ProcessingWorker, config: dict):
        super().__init__()
        self.config = config
        self.setWindowTitle(self.config.get("labels", {}).get("app_title", "Phần Mềm Bắn Súng"))
        self.setFocusPolicy(Qt.StrongFocus) 
        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)
        self.worker = worker
        self.db_manager = DatabaseManager()
        self.audio_manager = AudioManager()
        
        self.current_mode = 0 
        self.cameras = {1: None, 2: None}
        self.cam_indices = {1: 0, 2: 1}
        self.zoom_levels = {1: 1.0, 2: 1.0}
        self.calib_centers = {1: None, 2: None}
        self.is_calib_mode = {1: False, 2: False}
        self.clean_frames = {1: None, 2: None}
        self.shot_points = {1: None, 2: None}
        self.final_size = (480, 640)
        
        self.active_session_ids = {0: None, 1: None, 2: None}
        self.session_active_flags = {0: False, 1: False, 2: False}
        self.shot_counters = {0: 0, 1: 0, 2: 0}
        self.selected_soldiers = {0: None, 1: None, 2: None}
        self.testing_shot_buffer = {0: [], 1: [], 2: []}

        self.save_dir = os.path.join(APP_DATA_DIR, "captured_images")
        os.makedirs(self.save_dir, exist_ok=True)
        
        try: self.cam_indices[1] = int(self.config.get("camera_index", 0))
        except: pass

        self._init_connections()
        self.populate_trigger_selectors()
        self.reset_ui_state()

    # --- HÀM RESET HIỂN THỊ (FIXED: Dùng setPixmap rỗng) ---
    def reset_result_display(self):
        """Xóa ảnh kết quả và text điểm số về mặc định."""
        empty = QPixmap() # Ảnh rỗng
        
        # Single Mode
        self.gui.score_label.setText("Điểm số: --")
        self.gui.result_image_label.setPixmap(empty)
        self.gui.result_image_label.setText("Ảnh kết quả")
        
        # Dual Mode - Cam 1
        if hasattr(self.gui, 'dual_cam1_score'):
            self.gui.dual_cam1_score.setText("Điểm số: --")
            self.gui.dual_cam1_result_img.setPixmap(empty)
            self.gui.dual_cam1_result_img.setText("Ảnh kết quả")
            
        # Dual Mode - Cam 2
        if hasattr(self.gui, 'dual_cam2_score'):
            self.gui.dual_cam2_score.setText("Điểm số: --")
            self.gui.dual_cam2_result_img.setPixmap(empty)
            self.gui.dual_cam2_result_img.setText("Ảnh kết quả")

    def _update_session_btn(self, idx, active):
        txt = "KẾT THÚC" if active else "BẮT ĐẦU"
        obj = "danger" if active else ""
        is_testing = (self.gui.training_type_selector.currentData() == "TEST")
        
        if idx == 0: 
            btn = self.gui.session_button
            self.gui.btn_select_soldier.setEnabled(not active and not is_testing)
        elif idx == 1: 
            btn = self.gui.dual_cam1_session_btn
            self.gui.dual_cam1_btn_select.setEnabled(not active and not is_testing)
        else: 
            btn = self.gui.dual_cam2_session_btn
            self.gui.dual_cam2_btn_select.setEnabled(not active and not is_testing)
            
        btn.setText(txt); btn.setObjectName(obj); btn.style().polish(btn)
        
        any_active = any(self.session_active_flags.values())
        self.gui.mode_selector.setEnabled(not any_active)
        self.gui.training_type_selector.setEnabled(not any_active)
        self.gui.back_button.setEnabled(not any_active)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        trigger_action = None
        if key in [Qt.Key_VolumeUp, Qt.Key_Enter, Qt.Key_Return, Qt.Key_W, Qt.Key_Up]: trigger_action = 'UP'
        elif key in [Qt.Key_VolumeDown, Qt.Key_Space, Qt.Key_S, Qt.Key_Down]: trigger_action = 'DOWN'
        if trigger_action:
            event.accept(); logger.info(f"Trigger: {trigger_action}")
            self.handle_trigger_signal(trigger_action)
        else: super().keyPressEvent(event)

    def mousePressEvent(self, event): self.setFocus(); super().mousePressEvent(event)

    def populate_trigger_selectors(self):
        triggers = [("Cò L (Nút Lên)", "UP"), ("Cò N (Nút Xuống)", "DOWN")]
        if hasattr(self.gui, 'trigger_selector'):
            self.gui.trigger_selector.clear(); [self.gui.trigger_selector.addItem(t, v) for t,v in triggers]; self.gui.trigger_selector.setCurrentIndex(0)
        if hasattr(self.gui, 'dual_cam1_trigger'):
            self.gui.dual_cam1_trigger.clear(); [self.gui.dual_cam1_trigger.addItem(t, v) for t,v in triggers]; self.gui.dual_cam1_trigger.setCurrentIndex(0)
        if hasattr(self.gui, 'dual_cam2_trigger'):
            self.gui.dual_cam2_trigger.clear(); [self.gui.dual_cam2_trigger.addItem(t, v) for t,v in triggers]; self.gui.dual_cam2_trigger.setCurrentIndex(1)

    def _init_connections(self):
        self.gui.mode_selector.currentIndexChanged.connect(self.on_change_mode)
        self.gui.back_button.clicked.connect(self.close_and_reset)
        self.gui.training_type_selector.currentIndexChanged.connect(self.on_change_training_type)
        self.gui.btn_select_soldier.clicked.connect(lambda: self.open_select_soldier_dialog(0))
        self.gui.session_button.clicked.connect(lambda: self.toggle_session(0))
        self.gui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.gui.refresh_button.clicked.connect(lambda: self.refresh_cam(1))
        self.gui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.gui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.gui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        if hasattr(self.gui, 'dual_cam1_session_btn'):
            self.gui.dual_cam1_btn_select.clicked.connect(lambda: self.open_select_soldier_dialog(1))
            self.gui.dual_cam1_session_btn.clicked.connect(lambda: self.toggle_session(1))
            self.gui.dual_cam1_zoom.valueChanged.connect(lambda v: self.set_zoom(1, v))
            self.gui.dual_cam1_refresh.clicked.connect(lambda: self.refresh_cam(1))
            self.gui.dual_cam1_calib.clicked.connect(lambda: self.toggle_calib(1))
            self.gui.dual_cam1_view.clicked.connect(lambda p: self.set_center(1, p))
            self.gui.dual_cam1_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        if hasattr(self.gui, 'dual_cam2_session_btn'):
            self.gui.dual_cam2_btn_select.clicked.connect(lambda: self.open_select_soldier_dialog(2))
            self.gui.dual_cam2_session_btn.clicked.connect(lambda: self.toggle_session(2))
            self.gui.dual_cam2_zoom.valueChanged.connect(lambda v: self.set_zoom(2, v))
            self.gui.dual_cam2_refresh.clicked.connect(lambda: self.refresh_cam(2))
            self.gui.dual_cam2_calib.clicked.connect(lambda: self.toggle_calib(2))
            self.gui.dual_cam2_view.clicked.connect(lambda p: self.set_center(2, p))
            self.gui.dual_cam2_source.currentIndexChanged.connect(lambda i: self.change_cam_source(2, i))

    def on_change_training_type(self):
        is_testing = (self.gui.training_type_selector.currentData() == "TEST")
        if any(self.session_active_flags.values()): self.reset_ui_state()
        self.gui.soldier_container.setVisible(not is_testing)
        if hasattr(self.gui, 'dual_cam1_soldier_container'): self.gui.dual_cam1_soldier_container.setVisible(not is_testing)
        if hasattr(self.gui, 'dual_cam2_soldier_container'): self.gui.dual_cam2_soldier_container.setVisible(not is_testing)
        self._update_session_btn(0, self.session_active_flags[0])
        if hasattr(self.gui, 'dual_cam1_session_btn'): self._update_session_btn(1, self.session_active_flags[1])
        if hasattr(self.gui, 'dual_cam2_session_btn'): self._update_session_btn(2, self.session_active_flags[2])

    def open_select_soldier_dialog(self, session_idx):
        if self.session_active_flags[session_idx]:
            QMessageBox.warning(self, "Đang tập", "Vui lòng kết thúc phiên tập trước khi đổi người.")
            return
        soldiers = self.db_manager.get_all_soldiers()
        dialog = SelectSoldierDialog(soldiers, self)
        if dialog.exec() == QDialog.Accepted and dialog.selected_soldier:
            self.selected_soldiers[session_idx] = dialog.selected_soldier
            name_display = f"{dialog.selected_soldier['name']} - {dialog.selected_soldier.get('class_name', '')}"
            if session_idx == 0: self.gui.soldier_display.setText(name_display)
            elif session_idx == 1: self.gui.dual_cam1_soldier_display.setText(name_display)
            elif session_idx == 2: self.gui.dual_cam2_soldier_display.setText(name_display)
            self._reset_session_ui(session_idx)

    def populate_camera_sources(self):
        available = find_available_cameras()
        if not available: available = [0, 1]
        self.gui.single_cam_source.clear()
        if hasattr(self.gui, 'dual_cam1_source'):
            self.gui.dual_cam1_source.clear(); self.gui.dual_cam2_source.clear()
        for idx in available:
            text = f"Camera {idx}"
            self.gui.single_cam_source.addItem(text, idx)
            if hasattr(self.gui, 'dual_cam1_source'):
                self.gui.dual_cam1_source.addItem(text, idx); self.gui.dual_cam2_source.addItem(text, idx)
        self._sync_combo_selection(1); self._sync_combo_selection(2)

    def _sync_combo_selection(self, cam_id):
        current_idx = self.cam_indices.get(cam_id)
        if current_idx is None: return
        if cam_id == 1:
            idx = self.gui.single_cam_source.findData(current_idx)
            if idx >= 0: self.gui.single_cam_source.setCurrentIndex(idx)
            if hasattr(self.gui, 'dual_cam1_source'):
                idx = self.gui.dual_cam1_source.findData(current_idx)
                if idx >= 0: self.gui.dual_cam1_source.setCurrentIndex(idx)
        elif cam_id == 2:
            if hasattr(self.gui, 'dual_cam2_source'):
                idx = self.gui.dual_cam2_source.findData(current_idx)
                if idx >= 0: self.gui.dual_cam2_source.setCurrentIndex(idx)

    def change_cam_source(self, cam_id, combo_idx):
        combo = None
        if self.current_mode == 0 and cam_id == 1: combo = self.gui.single_cam_source
        elif self.current_mode == 1: combo = self.gui.dual_cam1_source if cam_id == 1 else self.gui.dual_cam2_source
        if not combo: return
        new_idx = combo.itemData(combo_idx)
        if new_idx is not None and new_idx != self.cam_indices[cam_id]:
            self.cam_indices[cam_id] = new_idx
            self.refresh_cam(cam_id)
            self.gui.single_cam_source.blockSignals(True)
            if hasattr(self.gui, 'dual_cam1_source'): self.gui.dual_cam1_source.blockSignals(True)
            self._sync_combo_selection(cam_id)
            self.gui.single_cam_source.blockSignals(False)
            if hasattr(self.gui, 'dual_cam1_source'): self.gui.dual_cam1_source.blockSignals(False)

    # --- FIX: TỰ ĐỘNG BẬT/TẮT CAM KHI CHUYỂN CHẾ ĐỘ ---
    def on_change_mode(self, idx):
        self.current_mode = idx
        self.gui.main_stack.setCurrentIndex(idx)
        
        # Reset kết quả để tránh nhầm lẫn
        self.reset_result_display()
        
        # Đồng bộ Zoom
        if idx == 0:
            current_zoom_1 = int(self.zoom_levels[1] * 10)
            self.gui.zoom_slider.setValue(current_zoom_1)
            # Về chế độ 1 -> Tắt Cam 2 để tiết kiệm tài nguyên
            self.stop_cam(2)
            
        elif idx == 1:
            current_zoom_1 = int(self.zoom_levels[1] * 10)
            if hasattr(self.gui, 'dual_cam1_zoom'): self.gui.dual_cam1_zoom.setValue(current_zoom_1)
            current_zoom_2 = int(self.zoom_levels[2] * 10)
            if hasattr(self.gui, 'dual_cam2_zoom'): self.gui.dual_cam2_zoom.setValue(current_zoom_2)
            
            # Vào chế độ 2 -> Bật Cam 2 (Force Refresh)
            self.refresh_cam(2)

    # --- HÀM DỪNG CAM AN TOÀN (MỚI) ---
    def stop_cam(self, cam_id):
        if self.cameras[cam_id] is not None:
            self.cameras[cam_id].stop()
            self.cameras[cam_id].deleteLater()
            self.cameras[cam_id] = None
            
            # Xóa màn hình hiển thị
            if cam_id == 2 and hasattr(self.gui, 'dual_cam2_view'):
                self.gui.dual_cam2_view.setText("Đã tắt")
                self.gui.dual_cam2_view.setPixmap(QPixmap())

    @Slot(object)
    def handle_camera_frame_1(self, frame): self._process_frame_logic(1, frame)
    @Slot(object)
    def handle_camera_frame_2(self, frame): 
        if self.current_mode == 1: self._process_frame_logic(2, frame)

    def _process_frame_logic(self, cam_id, frame):
        if frame is None: return
        cropped = self.crop_to_3_4(frame)
        zm = self.zoom_levels[cam_id]
        zoomed = self.apply_zoom(cropped, zm)
        self.clean_frames[cam_id] = zoomed
        h, w = zoomed.shape[:2]
        center = self.calib_centers[cam_id] if self.calib_centers[cam_id] else (w//2, h//2)
        self.shot_points[cam_id] = center
        display = zoomed.copy()
        cv2.drawMarker(display, center, (0,0,255), cv2.MARKER_CROSS, 20, 1)
        pix = self.gui._convert_cv_to_pixmap(display)
        if self.current_mode == 0:
            if cam_id == 1: self.gui.camera_view_label.setPixmap(pix)
        else:
            if cam_id == 1 and hasattr(self.gui, 'dual_cam1_view'): self.gui.dual_cam1_view.setPixmap(pix)
            elif cam_id == 2 and hasattr(self.gui, 'dual_cam2_view'): self.gui.dual_cam2_view.setPixmap(pix)

    def refresh_cam(self, cam_id):
        idx = self.cam_indices[cam_id]
        # Dừng thread cũ trước khi tạo mới
        if self.cameras[cam_id] is not None:
            self.cameras[cam_id].stop(); self.cameras[cam_id].deleteLater(); self.cameras[cam_id] = None
            QApplication.processEvents() # Đảm bảo việc dừng hoàn tất
            
        try:
            self.cameras[cam_id] = CameraThread(idx)
            if cam_id == 1: self.cameras[cam_id].frame_received.connect(self.handle_camera_frame_1)
            else: self.cameras[cam_id].frame_received.connect(self.handle_camera_frame_2)
            self.cameras[cam_id].start()
            logger.info(f"Đã khởi động CameraThread cho Cam {cam_id} (Index {idx})")
        except Exception as e: logger.error(f"Lỗi khởi động camera {cam_id}: {e}")

    def crop_to_3_4(self, frame):
        h, w = frame.shape[:2]; target_aspect = 3.0 / 4.0; new_w = int(h * target_aspect)
        if w > new_w: start_x = (w - new_w) // 2; cropped = frame[:, start_x : start_x + new_w]
        else: cropped = frame
        return cv2.resize(cropped, self.final_size, interpolation=cv2.INTER_LINEAR)

    def apply_zoom(self, frame, zoom):
        if zoom <= 1.0: return frame
        h, w = frame.shape[:2]; cw, ch = int(w/zoom), int(h/zoom); x, y = (w-cw)//2, (h-ch)//2
        return cv2.resize(frame[y:y+ch, x:x+cw], (w, h), interpolation=cv2.INTER_LINEAR)

    def set_zoom(self, cam_id, val): self.zoom_levels[cam_id] = val/10.0

    def toggle_calib(self, cam_id):
        s = not self.is_calib_mode[cam_id]; self.is_calib_mode[cam_id] = s
        lbl = "Lưu" if s else "Hiệu chỉnh"; cursor = Qt.CrossCursor if s else Qt.ArrowCursor
        if self.current_mode == 0 and cam_id == 1:
            self.gui.calibrate_button.setText(lbl); self.gui.camera_view_label.setCursor(cursor); self.gui.camera_view_label.set_calibration_mode(s)
        elif self.current_mode == 1:
            if cam_id == 1:
                self.gui.dual_cam1_calib.setText(lbl); self.gui.dual_cam1_view.setCursor(cursor); self.gui.dual_cam1_view.set_calibration_mode(s)
            else:
                self.gui.dual_cam2_calib.setText(lbl); self.gui.dual_cam2_view.setCursor(cursor); self.gui.dual_cam2_view.set_calibration_mode(s)

    def set_center(self, cam_id, pos):
        if self.current_mode == 0: view = self.gui.camera_view_label
        else: view = self.gui.dual_cam1_view if cam_id==1 else self.gui.dual_cam2_view
        if self.clean_frames[cam_id] is None: return
        h_img, w_img = self.clean_frames[cam_id].shape[:2]; w_wid, h_wid = view.width(), view.height()
        scale = min(w_wid/w_img, h_wid/h_img); dw, dh = int(w_img*scale), int(h_img*scale); ox, oy = (w_wid-dw)//2, (h_wid-dh)//2
        cx = int((pos.x() - ox) / scale); cy = int((pos.y() - oy) / scale)
        cx = max(0, min(cx, w_img-1)); cy = max(0, min(cy, h_img-1))
        self.calib_centers[cam_id] = (cx, cy)
        logger.info(f"Đã đặt tâm ngắm mới cho Cam {cam_id}: ({cx}, {cy})")
        self.toggle_calib(cam_id)

    def toggle_session(self, session_idx):
        if self.session_active_flags[session_idx]: self.finalize_session(session_idx)
        else:
            is_testing = (self.gui.training_type_selector.currentData() == "TEST")
            if not is_testing:
                data = self.selected_soldiers[session_idx]
                if not data: QMessageBox.warning(self, "Thông báo", "Vui lòng chọn người tập trước khi bắt đầu."); return
                sid = self.db_manager.create_session(data['id'])
            else:
                sid = -1; self.testing_shot_buffer[session_idx] = []
            
            if sid:
                # [FIX]: Reset hiển thị ngay khi bắt đầu phiên mới
                self.reset_result_display()
                
                self.active_session_ids[session_idx] = sid
                self.session_active_flags[session_idx] = True
                self.shot_counters[session_idx] = 0
                self._update_session_btn(session_idx, True)
            self.setFocus()

    def finalize_session(self, session_idx):
        sid = self.active_session_ids[session_idx]
        if not sid: return
        if sid > 0:
            shot_count = self.db_manager.get_shot_count_for_session(sid)
            if shot_count == 0:
                reply = QMessageBox.question(self, "Phiên tập trống", "Bạn chưa bắn phát nào. Xóa phiên này không?", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No: return
                self.db_manager.delete_session(sid)
            else:
                default_name = f"Phiên tập #{sid}"; soldier_id = None
                data = self.selected_soldiers[session_idx]
                if data: soldier_id = data['id']
                while True:
                    name, ok = QInputDialog.getText(self, "Lưu Phiên Tập", "Nhập tên:", QLineEdit.Normal, default_name)
                    if not ok: return
                    final_name = name.strip() if name.strip() else default_name
                    if soldier_id and self.db_manager.session_name_exists(final_name, soldier_id):
                        QMessageBox.warning(self, "Tên trùng", "Tên đã tồn tại."); continue
                    self.db_manager.update_session_name(sid, final_name); break
                self.db_manager.end_session(sid)
        self.session_active_flags[session_idx] = False
        self.active_session_ids[session_idx] = None
        self._update_session_btn(session_idx, False)

    def _reset_session_ui(self, idx):
        if self.session_active_flags[idx]: self.finalize_session(idx)

    def reset_ui_state(self):
        self.gui.clear_video_feed("Chờ Camera...")
        for i in [0, 1, 2]:
            if self.session_active_flags[i]:
                sid = self.active_session_ids[i]
                if sid and sid > 0: self.db_manager.end_session(sid)
                self.session_active_flags[i] = False
                self.active_session_ids[i] = None
                self._update_session_btn(i, False)

    def start_camera(self):
        self.populate_camera_sources()
        self.refresh_cam(1)
        if self.current_mode == 1: self.refresh_cam(2)
        self.setFocus()

    def shutdown_components(self):
        for cam_id in [1, 2]:
            if self.cameras[cam_id]: self.cameras[cam_id].stop(); self.cameras[cam_id].deleteLater(); self.cameras[cam_id] = None
        self.reset_ui_state()

    def close_and_reset(self):
        self.shutdown_components()
        self.close()

    def handle_trigger_signal(self, key_type):
        if self.current_mode == 0: 
            sel = self.gui.trigger_selector.currentData()
            if sel == key_type: self.capture_single_cam(1, session_idx=0)
        elif self.current_mode == 1: 
            if hasattr(self.gui, 'dual_cam1_trigger'):
                sel1 = self.gui.dual_cam1_trigger.currentData()
                if sel1 == key_type: self.capture_single_cam(1, session_idx=1)
            if hasattr(self.gui, 'dual_cam2_trigger'):
                sel2 = self.gui.dual_cam2_trigger.currentData()
                if sel2 == key_type: self.capture_single_cam(2, session_idx=2)

    def capture_single_cam(self, cam_id, session_idx):
        if self.clean_frames[cam_id] is not None:
            frame_to_save = self.clean_frames[cam_id].copy()
            self.audio_manager.play_sound('shot')
            self._send_to_worker(cam_id, frame_to_save, session_idx)

    def _send_to_worker(self, cam_id, frame, session_idx):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"s{session_idx}_cam{cam_id}_{ts}.png"
        path = os.path.join(self.save_dir, filename)
        try:
            cv2.imwrite(path, frame)
            self.request_processing.emit(frame, self.shot_points[cam_id], path)
        except Exception as e:
            logger.error(f"Lỗi chụp ảnh: {e}")

    @Slot(dict)
    def on_processing_finished(self, res):
        score = res.get('score')
        path = res.get('image_path', '')
        session_idx = 0
        try:
            name = os.path.basename(path)
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass

        if score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')
        
        pix = self.gui._convert_cv_to_pixmap(res.get('result_frame'))
        
        is_testing = (self.gui.training_type_selector.currentData() == "TEST")
        score_text = f"Điểm số: {score}"
        if is_testing:
             count = len(self.testing_shot_buffer[session_idx]) + 1
             score_text = f"Điểm: {score} (Phát {count}/3)"

        if session_idx == 0:
            self.gui.score_label.setText(score_text)
            self.gui.result_image_label.setPixmap(pix)
        elif session_idx == 1:
            if hasattr(self.gui, 'dual_cam1_score'):
                self.gui.dual_cam1_score.setText(score_text)
                self.gui.dual_cam1_result_img.setPixmap(pix)
        elif session_idx == 2:
            if hasattr(self.gui, 'dual_cam2_score'):
                self.gui.dual_cam2_score.setText(score_text)
                self.gui.dual_cam2_result_img.setPixmap(pix)
        
        QApplication.processEvents()

        sid = self.active_session_ids[session_idx]
        if sid and self.session_active_flags[session_idx]:
            self.shot_counters[session_idx] += 1
            if sid > 0:
                self.db_manager.add_shot(sid, self.shot_counters[session_idx], score, 
                                         res.get('target_detected_raw'), res.get('coords'), path)
            else:
                cv_frame = res.get('result_frame')
                pix_frame = self.gui._convert_cv_to_pixmap(cv_frame)
                self.testing_shot_buffer[session_idx].append({
                    'score': score, 
                    'image': pix_frame
                })
                if len(self.testing_shot_buffer[session_idx]) >= 3:
                    cam_title = f"KẾT QUẢ - CAMERA {session_idx}" if self.current_mode == 1 else ""
                    popup = ResultPopup(self.testing_shot_buffer[session_idx], camera_name=cam_title, parent=self)
                    popup.exec()
                    
                    # [FIX]: Reset hiển thị sau khi đóng popup
                    self.reset_result_display()
                    
                    self.testing_shot_buffer[session_idx] = []
                    self.shot_counters[session_idx] = 0