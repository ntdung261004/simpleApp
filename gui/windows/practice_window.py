# file: gui/windows/practice_window.py

import logging
from PySide6.QtWidgets import (
    QMainWindow, QMessageBox, QInputDialog, QLineEdit, QDialog, QVBoxLayout, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, 
    QDialogButtonBox, QLabel, QHBoxLayout, QPushButton, QWidget, QApplication
)
from PySide6.QtCore import Signal, Slot, Qt, QSize, QTimer
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
from core.triggers import BluetoothTrigger

logger = logging.getLogger(__name__)

# --- CLASS RESULT POPUP (GIỮ NGUYÊN) ---
# ... (Giữ nguyên code class ResultPopup) ...
class ResultPopup(QDialog):
    def __init__(self, shots_data, camera_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle("KẾT QUẢ LUYỆN TẬP")
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
        if total_score < 15: rank = "KHÔNG ĐẠT"; color = "#95a5a6"
        elif 15 <= total_score <= 18: rank = "ĐẠT"; color = "#f39c12"
        elif 19 <= total_score <= 23: rank = "KHÁ"; color = "#3498db"
        else: rank = "GIỎI"; color = "#2ecc71"

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

# --- PRACTICE WINDOW CHÍNH ---
class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)
    back_to_menu_signal = Signal()

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
        
        self.bt_trigger = BluetoothTrigger()
        self.bt_trigger.triggered.connect(self.execute_shot_logic)
        self.bt_trigger.start_global_listener()
        self.bt_trigger.activate()
        
        self.is_free_practice = False
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
        self.testing_shot_buffer = {0: [], 1: [], 2: []}
        self.pending_shots = {0: 0, 1: 0, 2: 0}
        self.next_shot_cam_id = 1 

        self.save_dir = os.path.join(APP_DATA_DIR, "captured_images")
        os.makedirs(self.save_dir, exist_ok=True)
        
        try: self.cam_indices[1] = int(self.config.get("camera_index", 0))
        except: pass

        self._init_connections()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def start_camera(self):
        logger.info("PracticeWindow: Start (Dashboard Mode)")
        self.populate_camera_sources()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)
        self.setFocus()

    def _init_connections(self):
        self.gui.btn_create_session.clicked.connect(self.on_session_practice_clicked)
        self.gui.btn_free_practice.clicked.connect(self.on_free_practice_clicked)
        self.gui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)

        self.gui.btn_new_session.clicked.connect(self.on_new_session_clicked)
        self.gui.btn_continue_session.clicked.connect(self.on_continue_session_clicked)
        self.gui.btn_back_dashboard_session.clicked.connect(self.on_back_to_dashboard)

        self.gui.back_to_dashboard_btn.clicked.connect(self.on_return_to_dashboard)
        self.gui.mode_selector.currentIndexChanged.connect(self.on_change_mode)
        self.gui.shooting_mode_selector.currentIndexChanged.connect(self.on_change_shooting_mode)
        
        self.gui.session_button.clicked.connect(lambda: self.toggle_session(0))
        self.gui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.gui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.gui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.gui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.gui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        
        if hasattr(self.gui, 'dual_cam1_session_btn'):
            self.gui.dual_cam1_session_btn.clicked.connect(lambda: self.toggle_session(1))
            self.gui.dual_cam1_zoom.valueChanged.connect(lambda v: self.set_zoom(1, v))
            self.gui.dual_cam1_refresh.clicked.connect(lambda: self.on_manual_refresh(1))
            self.gui.dual_cam1_calib.clicked.connect(lambda: self.toggle_calib(1))
            self.gui.dual_cam1_view.clicked.connect(lambda p: self.set_center(1, p))
            self.gui.dual_cam1_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
            
        if hasattr(self.gui, 'dual_cam2_session_btn'):
            self.gui.dual_cam2_session_btn.clicked.connect(lambda: self.toggle_session(2))
            self.gui.dual_cam2_zoom.valueChanged.connect(lambda v: self.set_zoom(2, v))
            self.gui.dual_cam2_refresh.clicked.connect(lambda: self.on_manual_refresh(2))
            self.gui.dual_cam2_calib.clicked.connect(lambda: self.toggle_calib(2))
            self.gui.dual_cam2_view.clicked.connect(lambda p: self.set_center(2, p))
            self.gui.dual_cam2_source.currentIndexChanged.connect(lambda i: self.change_cam_source(2, i))

    def on_session_practice_clicked(self):
        self.gui.stack.setCurrentWidget(self.gui.page_session_menu)

    def on_back_to_dashboard(self):
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def on_new_session_clicked(self):
        QMessageBox.information(self, "Thông báo", "Chức năng 'Bắt đầu phiên tập mới' sẽ được thực hiện ở bước sau.")

    def on_continue_session_clicked(self):
        QMessageBox.information(self, "Thông báo", "Chức năng 'Tiếp tục phiên tập đã lưu' sẽ được thực hiện ở bước sau.")

    def on_free_practice_clicked(self):
        logger.info("Vào chế độ: Luyện tập tự do")
        self.is_free_practice = True
        self.populate_camera_sources()
        self.gui.stack.setCurrentWidget(self.gui.page_view)
        
        if self.current_mode == 0: self.refresh_cam(1)
        else: self.refresh_cam(1); self.refresh_cam(2)
        
        self._update_button_visibility()

    def on_return_to_dashboard(self):
        self.shutdown_components()
        self.is_free_practice = False
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def reset_ui_state(self):
        self.gui.clear_video_feed("Chờ Camera...")
        self.next_shot_cam_id = 1 
        self.update_active_cam_indicator() 
        for i in [0, 1, 2]:
            if self.session_active_flags[i]:
                sid = self.active_session_ids[i]
                if sid and sid > 0: self.db_manager.end_session(sid)
                self.session_active_flags[i] = False
                self.active_session_ids[i] = None
                self._update_session_btn(i, False)
                self.shot_counters[i] = 0
                self.testing_shot_buffer[i] = []
                self.pending_shots[i] = 0
                self.reset_result_display(i)

    def _update_button_visibility(self):
        shooting_mode = self.gui.shooting_mode_selector.currentData()
        should_hide = self.is_free_practice and (shooting_mode == "SINGLE")
        
        def set_visible(btn, visible):
            if btn: btn.setVisible(visible)

        set_visible(self.gui.session_button, not should_hide)
        
        if hasattr(self.gui, 'dual_cam1_session_btn'):
            set_visible(self.gui.dual_cam1_session_btn, not should_hide)
            
        if hasattr(self.gui, 'dual_cam2_session_btn'):
            set_visible(self.gui.dual_cam2_session_btn, not should_hide)

    def on_change_shooting_mode(self):
        for idx in [0, 1, 2]:
            if self.session_active_flags[idx]:
                self.finalize_session(idx)
            
            self.reset_result_display(idx)
            self.testing_shot_buffer[idx] = []
            self.pending_shots[idx] = 0
            self.shot_counters[idx] = 0
            
        self._update_button_visibility()

    def on_change_mode(self, idx):
        self.current_mode = idx
        self.gui.main_stack.setCurrentIndex(idx)
        self.reset_result_display()
        self.next_shot_cam_id = 1 
        self.update_active_cam_indicator() 
        self._validate_and_sync_selection(1)
        self._validate_and_sync_selection(2)
        
        if idx == 0: 
            self.stop_cam(2) 
            self.refresh_cam(1)
        elif idx == 1: 
            if self.cam_indices[1] == self.cam_indices[2]:
                available_cams = find_available_cameras()
                for c in available_cams:
                    if c != self.cam_indices[1]:
                        self.cam_indices[2] = c
                        break
                self._validate_and_sync_selection(2)
            self.refresh_cam(1)
            self.refresh_cam(2)
            
        self._update_button_visibility()

    def toggle_session(self, session_idx):
        if self.session_active_flags[session_idx]: self.finalize_session(session_idx)
        else:
            sid = -1
            self.reset_result_display(session_idx)
            self.active_session_ids[session_idx] = sid
            self.session_active_flags[session_idx] = True
            self.shot_counters[session_idx] = 0
            self.testing_shot_buffer[session_idx] = []
            self.pending_shots[session_idx] = 0
            
            self._update_session_btn(session_idx, True)
            self.setFocus()

    def finalize_session(self, session_idx):
        sid = self.active_session_ids[session_idx]
        if not self.is_free_practice and sid and sid > 0:
            shot_count = self.db_manager.get_shot_count_for_session(sid)
            if shot_count == 0: self.db_manager.delete_session(sid)
            else: self.db_manager.end_session(sid)

        self.session_active_flags[session_idx] = False
        self.active_session_ids[session_idx] = None
        self._update_session_btn(session_idx, False)

    def reset_result_display(self, session_idx=None):
        empty = QPixmap()
        if session_idx is None or session_idx == 0:
            self.gui.score_label.setText("Điểm số: --")
            self.gui.result_image_label.setPixmap(empty)
            self.gui.result_image_label.setText("Ảnh kết quả")
        if (session_idx is None or session_idx == 1) and hasattr(self.gui, 'dual_cam1_score'):
            self.gui.dual_cam1_score.setText("Điểm số: --")
            self.gui.dual_cam1_result_img.setPixmap(empty)
            self.gui.dual_cam1_result_img.setText("Ảnh kết quả")
        if (session_idx is None or session_idx == 2) and hasattr(self.gui, 'dual_cam2_score'):
            self.gui.dual_cam2_score.setText("Điểm số: --")
            self.gui.dual_cam2_result_img.setPixmap(empty)
            self.gui.dual_cam2_result_img.setText("Ảnh kết quả")

    def _update_session_btn(self, idx, active):
        txt = "KẾT THÚC" if active else "BẮT ĐẦU"
        obj = "danger" if active else ""
        if idx == 0: btn = self.gui.session_button
        elif idx == 1: btn = self.gui.dual_cam1_session_btn
        else: btn = self.gui.dual_cam2_session_btn
        btn.setText(txt); btn.setObjectName(obj); btn.style().polish(btn)
        
        any_active = any(self.session_active_flags.values())
        self.gui.mode_selector.setEnabled(not any_active)
        self.gui.shooting_mode_selector.setEnabled(not any_active)
        self.gui.back_to_dashboard_btn.setEnabled(not any_active)

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        if key in [Qt.Key_Enter, Qt.Key_Return]:
            event.accept(); self.execute_shot_logic()
        else: super().keyPressEvent(event)

    def mousePressEvent(self, event): self.setFocus(); super().mousePressEvent(event)

    def on_manual_refresh(self, cam_id):
        self.populate_camera_sources()
        self.refresh_cam(cam_id)

    def populate_camera_sources(self):
        available = find_available_cameras()
        if not available: available = [0, 1]
        self.gui.single_cam_source.blockSignals(True)
        if hasattr(self.gui, 'dual_cam1_source'):
            self.gui.dual_cam1_source.blockSignals(True)
            self.gui.dual_cam2_source.blockSignals(True)
        combos = [self.gui.single_cam_source]
        if hasattr(self.gui, 'dual_cam1_source'):
            combos.append(self.gui.dual_cam1_source)
            combos.append(self.gui.dual_cam2_source)
        for combo in combos:
            combo.clear()
            for idx in available:
                combo.addItem(f"Camera {idx}", idx)
        self._validate_and_sync_selection(1)
        self._validate_and_sync_selection(2)
        self.gui.single_cam_source.blockSignals(False)
        if hasattr(self.gui, 'dual_cam1_source'):
            self.gui.dual_cam1_source.blockSignals(False)
            self.gui.dual_cam2_source.blockSignals(False)

    def _validate_and_sync_selection(self, cam_id):
        current_idx = self.cam_indices.get(cam_id)
        combo = None
        if self.current_mode == 0 and cam_id == 1:
            combo = self.gui.single_cam_source
        elif self.current_mode == 1:
            if cam_id == 1 and hasattr(self.gui, 'dual_cam1_source'): combo = self.gui.dual_cam1_source
            elif cam_id == 2 and hasattr(self.gui, 'dual_cam2_source'): combo = self.gui.dual_cam2_source
        if not combo: return
        idx_in_combo = combo.findData(current_idx)
        if idx_in_combo >= 0:
            combo.setCurrentIndex(idx_in_combo)
        else:
            if combo.count() > 0:
                combo.setCurrentIndex(0)
                new_idx = combo.itemData(0)
                self.cam_indices[cam_id] = new_idx

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
            if hasattr(self.gui, 'dual_cam1_source'):
                self.gui.dual_cam1_source.blockSignals(True)
                self.gui.dual_cam2_source.blockSignals(True)
            self._validate_and_sync_selection(1)
            self._validate_and_sync_selection(2)
            self.gui.single_cam_source.blockSignals(False)
            if hasattr(self.gui, 'dual_cam1_source'):
                self.gui.dual_cam1_source.blockSignals(False)
                self.gui.dual_cam2_source.blockSignals(False)

    def stop_cam(self, cam_id):
        self.clean_frames[cam_id] = None
        if self.cameras[cam_id] is not None:
            self.cameras[cam_id].stop()
            self.cameras[cam_id].deleteLater()
            self.cameras[cam_id] = None
            msg = "Đã tắt"
            if self.current_mode == 0:
                if cam_id == 1: self.gui.clear_video_feed(msg)
            else:
                empty = QPixmap()
                if cam_id == 1 and hasattr(self.gui, 'dual_cam1_view'): 
                    self.gui.dual_cam1_view.setPixmap(empty); self.gui.dual_cam1_view.setText(msg)
                elif cam_id == 2 and hasattr(self.gui, 'dual_cam2_view'):
                    self.gui.dual_cam2_view.setPixmap(empty); self.gui.dual_cam2_view.setText(msg)

    @Slot(int)
    def on_camera_error(self, cam_index):
        affected_cam_ids = []
        if self.cam_indices[1] == cam_index: affected_cam_ids.append(1)
        if self.cam_indices[2] == cam_index: affected_cam_ids.append(2)
        if not affected_cam_ids: return
        err_msg = "MẤT KẾT NỐI CAMERA!\nVui lòng kiểm tra dây cáp\nvà nhấn 'Làm mới'"
        err_style = "background-color: #34495e; color: #e74c3c; font-weight: bold; border: 2px solid #e74c3c;"
        for cam_id in affected_cam_ids:
            self.stop_cam(cam_id)
            if self.current_mode == 0:
                if cam_id == 1: 
                    self.gui.camera_view_label.setText(err_msg)
                    self.gui.camera_view_label.setStyleSheet(err_style)
            else:
                if cam_id == 1 and hasattr(self.gui, 'dual_cam1_view'):
                    self.gui.dual_cam1_view.setText(err_msg)
                    self.gui.dual_cam1_view.setStyleSheet(err_style)
                elif cam_id == 2 and hasattr(self.gui, 'dual_cam2_view'):
                    self.gui.dual_cam2_view.setText(err_msg)
                    self.gui.dual_cam2_view.setStyleSheet(err_style)

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
        default_style = "background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;"
        if self.current_mode == 0 and cam_id == 1:
             if "e74c3c" in self.gui.camera_view_label.styleSheet():
                 self.gui.camera_view_label.setStyleSheet(default_style)
        color = (0, 0, 255) 
        cv2.drawMarker(display, center, color, cv2.MARKER_CROSS, 20, 1)
        pix = self.gui._convert_cv_to_pixmap(display)
        if self.current_mode == 0:
            if cam_id == 1: self.gui.camera_view_label.setPixmap(pix)
        else:
            if cam_id == 1 and hasattr(self.gui, 'dual_cam1_view'): 
                self.gui.dual_cam1_view.setPixmap(pix)
                if "e74c3c" in self.gui.dual_cam1_view.styleSheet(): self.gui.dual_cam1_view.setStyleSheet(default_style)
            elif cam_id == 2 and hasattr(self.gui, 'dual_cam2_view'): 
                self.gui.dual_cam2_view.setPixmap(pix)
                if "e74c3c" in self.gui.dual_cam2_view.styleSheet(): self.gui.dual_cam2_view.setStyleSheet(default_style)

    def refresh_cam(self, cam_id):
        idx = self.cam_indices[cam_id]
        if self.cameras[cam_id] is not None:
            self.cameras[cam_id].stop(); self.cameras[cam_id].deleteLater(); self.cameras[cam_id] = None
            QApplication.processEvents()
        try:
            self.cameras[cam_id] = CameraThread(idx)
            if cam_id == 1: self.cameras[cam_id].frame_received.connect(self.handle_camera_frame_1)
            else: self.cameras[cam_id].frame_received.connect(self.handle_camera_frame_2)
            self.cameras[cam_id].error_occurred.connect(self.on_camera_error)
            self.cameras[cam_id].start()
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
        self.toggle_calib(cam_id)

    def shutdown_components(self):
        if self.bt_trigger:
            self.bt_trigger.deactivate()
            self.bt_trigger.stop_global_listener()
        for cam_id in [1, 2]:
            self.stop_cam(cam_id)
        self.reset_ui_state()

    def close_and_reset(self):
        self.shutdown_components()
        self.close()

    def update_active_cam_indicator(self):
        if self.current_mode == 0: return 
        if self.current_mode == 1:
            if hasattr(self.gui, 'dual_cam1_view') and hasattr(self.gui, 'dual_cam2_view'):
                self.gui.dual_cam1_view.set_active_border(self.next_shot_cam_id == 1)
                self.gui.dual_cam2_view.set_active_border(self.next_shot_cam_id == 2)

    @Slot() 
    def execute_shot_logic(self):
        if self.current_mode == 0:
            self.capture_single_cam(1, session_idx=0)
        elif self.current_mode == 1:
            target_cam = self.next_shot_cam_id
            shooting_mode = self.gui.shooting_mode_selector.currentData()
            
            if shooting_mode == "BURST_3":
                current_shots = len(self.testing_shot_buffer[target_cam])
                pending = self.pending_shots[target_cam]
                if current_shots + pending >= 3:
                    other_cam = 2 if target_cam == 1 else 1
                    other_total = len(self.testing_shot_buffer[other_cam]) + self.pending_shots[other_cam]
                    if other_total < 3:
                        target_cam = other_cam
                    else:
                        logger.warning("Cả 2 Camera đã đầy. Đợi kết quả.")
                        return

            success = self.capture_single_cam(target_cam, session_idx=target_cam)
            if success:
                self.next_shot_cam_id = 2 if target_cam == 1 else 1
                self.update_active_cam_indicator()

    def capture_single_cam(self, cam_id, session_idx):
        if self.clean_frames[cam_id] is None:
            QMessageBox.warning(self, "Lỗi Camera", f"Camera {cam_id} đang mất kết nối.")
            return False
        
        shooting_mode = self.gui.shooting_mode_selector.currentData()
        if shooting_mode == "BURST_3":
            current = len(self.testing_shot_buffer[session_idx])
            pending = self.pending_shots[session_idx]
            if current + pending >= 3:
                return False 

        frame_to_save = self.clean_frames[cam_id].copy()
        if shooting_mode == "BURST_3":
            self.pending_shots[session_idx] += 1
            
        self.audio_manager.play_sound('shot')
        self._send_to_worker(cam_id, frame_to_save, session_idx)
        return True

    def _send_to_worker(self, cam_id, frame, session_idx):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"s{session_idx}_cam{cam_id}_{ts}.png"
        path = os.path.join(self.save_dir, filename)
        try:
            cv2.imwrite(path, frame)
            self.request_processing.emit(frame, self.shot_points[cam_id], path)
        except Exception as e:
            logger.error(f"Lỗi chụp ảnh: {e}")
            self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)

    @Slot(dict)
    def on_processing_finished(self, res):
        score = res.get('score')
        session_idx = 0
        try:
            name = os.path.basename(res.get('image_path', ''))
            if name.startswith('s'): session_idx = int(name.split('_')[0][1:])
        except: pass
        
        self.pending_shots[session_idx] = max(0, self.pending_shots[session_idx] - 1)

        if score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')
        
        pix = self.gui._convert_cv_to_pixmap(res.get('result_frame'))
        
        shooting_mode = self.gui.shooting_mode_selector.currentData()
        
        score_text = f"Điểm: {score}"
        if shooting_mode == "BURST_3":
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
        
        if not self.is_free_practice and sid and sid > 0:
            pass
        else:
            if shooting_mode == "SINGLE":
                pass
                
            elif shooting_mode == "BURST_3":
                cv_frame = res.get('result_frame')
                pix_frame = self.gui._convert_cv_to_pixmap(cv_frame)
                self.testing_shot_buffer[session_idx].append({
                    'score': score, 
                    'image': pix_frame
                })
                
                if self.current_mode == 0:
                    if len(self.testing_shot_buffer[0]) >= 3:
                        self.show_test_result(0)
                        
                elif self.current_mode == 1:
                    buf1 = len(self.testing_shot_buffer[1])
                    buf2 = len(self.testing_shot_buffer[2])
                    pen1 = self.pending_shots[1]
                    pen2 = self.pending_shots[2]
                    
                    if buf1 >= 3 and buf2 >= 3 and pen1 == 0 and pen2 == 0:
                        self.show_test_result(1) 
                        self.show_test_result(2) 
                        self.next_shot_cam_id = 1
                        self.update_active_cam_indicator()

    def show_test_result(self, session_idx):
        buffer_data = self.testing_shot_buffer[session_idx]
        if not buffer_data: return

        cam_title = ""
        if self.current_mode == 1:
            cam_title = f"KẾT QUẢ - CAMERA {session_idx}"
            
        popup = ResultPopup(buffer_data, camera_name=cam_title, parent=self)
        popup.exec() 
        
        self.reset_result_display(session_idx)
        self.testing_shot_buffer[session_idx] = [] 
        self.shot_counters[session_idx] = 0
        self.pending_shots[session_idx] = 0