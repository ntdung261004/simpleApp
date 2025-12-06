# file: gui/controllers/shooting_controller.py
import os
import cv2
import logging
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Qt
from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtGui import QPixmap, QImage
from utils.camera import find_available_cameras
from config import APP_DATA_DIR
from gui.dialogs import ResultPopup

logger = logging.getLogger(__name__)

class ShootingController(QObject):
    def __init__(self, ui, config, worker, trigger, cam_manager, sess_manager, audio_manager, parent_window):
        super().__init__()
        self.ui = ui
        self.config = config
        self.worker = worker
        self.trigger = trigger
        self.cam_manager = cam_manager
        self.sess_manager = sess_manager
        self.audio_manager = audio_manager
        self.parent_window = parent_window
        self.save_dir = os.path.join(APP_DATA_DIR, "captured_images")
        os.makedirs(self.save_dir, exist_ok=True)
        self._connect_signals()

    def _connect_signals(self):
        # UI Signals
        self.ui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.ui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.ui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.ui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.ui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        
        # Dual Cam UI Signals
        if hasattr(self.ui, 'dual_cam1_view'):
            self.ui.dual_cam1_zoom.valueChanged.connect(lambda v: self.set_zoom(1, v))
            self.ui.dual_cam1_refresh.clicked.connect(lambda: self.on_manual_refresh(1))
            self.ui.dual_cam1_calib.clicked.connect(lambda: self.toggle_calib(1))
            self.ui.dual_cam1_view.clicked.connect(lambda p: self.set_center(1, p))
            self.ui.dual_cam1_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
            
        if hasattr(self.ui, 'dual_cam2_view'):
            self.ui.dual_cam2_zoom.valueChanged.connect(lambda v: self.set_zoom(2, v))
            self.ui.dual_cam2_refresh.clicked.connect(lambda: self.on_manual_refresh(2))
            self.ui.dual_cam2_calib.clicked.connect(lambda: self.toggle_calib(2))
            self.ui.dual_cam2_view.clicked.connect(lambda p: self.set_center(2, p))
            self.ui.dual_cam2_source.currentIndexChanged.connect(lambda i: self.change_cam_source(2, i))

        # Manager Signals
        self.cam_manager.frame_received.connect(self.update_camera_feed)
        self.cam_manager.error_occurred.connect(self.show_camera_error)
        
        self.sess_manager.session_state_changed.connect(self.update_session_ui_state)
        self.sess_manager.shot_added.connect(self.update_shot_display)
        self.sess_manager.burst_completed.connect(self.show_result_popup)
        self.sess_manager.auto_switch_camera.connect(self.update_active_border)

        self.trigger.triggered.connect(self.execute_shot_logic)

    @Slot(int, bool)
    def update_session_ui_state(self, idx, active):
        pass

    def start_free_practice(self):
        logger.info("Controller: Bắt đầu luyện tập tự do")
        self.sess_manager.is_free_practice = True
        self.sess_manager.shooting_mode = "SINGLE"
        
        self.populate_camera_sources()
        
        self.ui.shooting_mode_selector.setCurrentIndex(0)
        self.ui.mode_selector.setCurrentIndex(0)
        self._start_cameras()
        self.start_new_session(0)
        self.trigger.activate()

    def stop_practice(self):
        self.trigger.deactivate()
        self.cam_manager.stop_all()
        self.sess_manager.reset_all()
        self.reset_ui_state()

    def handle_mode_change(self, idx):
        self.sess_manager.current_mode = idx
        self.ui.main_stack.setCurrentIndex(idx)
        self.sess_manager.reset_all()
        self.reset_result_display()
        
        self.populate_camera_sources()
        
        if idx == 1:
            if self.cam_manager.cam_indices[1] == self.cam_manager.cam_indices[2]:
                available = find_available_cameras()
                if len(available) >= 2:
                    new_idx = available[1] if available[0] == self.cam_manager.cam_indices[1] else available[0]
                    self.cam_manager.cam_indices[2] = new_idx
                    self._sync_combo_selection(2)

        self._start_cameras()
        
        if idx == 0: self.start_new_session(0)
        else:
            self.start_new_session(1)
            self.start_new_session(2)

    def handle_shooting_mode_change(self):
        self.sess_manager.shooting_mode = self.ui.shooting_mode_selector.currentData()
        self.sess_manager.reset_all()
        self.reset_result_display()
        
        if self.sess_manager.current_mode == 0: self.start_new_session(0)
        else:
            self.start_new_session(1)
            self.start_new_session(2)

    def _start_cameras(self):
        if self.sess_manager.current_mode == 0:
            self.cam_manager.stop_camera(2)
            self.cam_manager.start_camera(1)
        else:
            self.cam_manager.start_camera(1)
            self.cam_manager.start_camera(2)

    def start_new_session(self, idx):
        self.reset_result_display(idx)
        self.sess_manager.start_session(idx)
        self.parent_window.setFocus()

    def on_manual_refresh(self, cam_id):
        self.cam_manager.stop_camera(cam_id)
        QApplication.processEvents()
        self.populate_camera_sources()
        self.cam_manager.start_camera(cam_id)

    def populate_camera_sources(self):
        available = find_available_cameras()
        if not available: available = [] 
        
        combos = [self.ui.single_cam_source]
        if hasattr(self.ui, 'dual_cam1_source'):
            combos.extend([self.ui.dual_cam1_source, self.ui.dual_cam2_source])
        
        for combo in combos:
            combo.blockSignals(True)
            current_data = combo.currentData() 
            combo.clear()
            
            if not available:
                combo.addItem("Không tìm thấy Cam", -1)
            else:
                for idx in available:
                    combo.addItem(f"Camera {idx}", idx)
            
            if current_data is not None and current_data in available:
                index_in_combo = combo.findData(current_data)
                combo.setCurrentIndex(index_in_combo)
            elif available:
                combo.setCurrentIndex(0)
                
            combo.blockSignals(False)
            
        self._sync_combo_selection(1)
        self._sync_combo_selection(2)

    def _sync_combo_selection(self, cam_id):
        combo = self._get_combo(cam_id)
        if not combo: return
        current_idx = combo.currentData()
        if current_idx is not None and current_idx != -1:
            self.cam_manager.cam_indices[cam_id] = current_idx

    def change_cam_source(self, cam_id, idx):
        combo = self._get_combo(cam_id)
        if combo:
            val = combo.itemData(idx)
            if val is not None and val != -1:
                self.cam_manager.cam_indices[cam_id] = val
                self.cam_manager.start_camera(cam_id)

    @Slot()
    def execute_shot_logic(self):
        target_cam = 1
        if self.sess_manager.current_mode == 1:
            target_cam = self.sess_manager.next_shot_cam_id
            next_t = self.sess_manager.get_auto_switch_target(target_cam)
            if next_t == -1: return 
            if next_t: target_cam = next_t

        session_idx = 0 if self.sess_manager.current_mode == 0 else target_cam
        if not self.sess_manager.check_can_shot(session_idx): return

        if not self.cam_manager.is_camera_ready(target_cam):
            # Log nhưng không popup để tránh spam
            return

        frame, center = self.cam_manager.get_shot_data(target_cam)
        if frame is None: return

        self.sess_manager.register_pending_shot(session_idx)
        self.audio_manager.play_sound('shot')

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fname = f"s{session_idx}_cam{target_cam}_{ts}.png"
        path = os.path.join(self.save_dir, fname)
        
        try:
            cv2.imwrite(path, frame)
            self.parent_window.request_processing.emit(frame, center, path)
        except Exception as e:
            logger.error(f"Lỗi chụp ảnh: {e}")
            self.sess_manager.rollback_pending_shot(session_idx)

        if self.sess_manager.current_mode == 1:
            self.sess_manager.next_shot_cam_id = 2 if target_cam == 1 else 1
            self.update_active_border(self.sess_manager.next_shot_cam_id)

    @Slot(dict)
    def on_processing_finished(self, res):
        pix = self._convert_cv_to_pixmap(res.get('result_frame'))
        score = res.get('score', 0)
        sess_idx = 0
        try:
            name = os.path.basename(res.get('image_path', ''))
            if name.startswith('s'): sess_idx = int(name.split('_')[0][1:])
        except: pass

        self._update_result_image(sess_idx, pix)
        if score > 0: self.audio_manager.play_score(score)
        else: self.audio_manager.play_sound('miss')
        self.sess_manager.process_shot_result(res, pix)

    # --- TINH CHỈNH: CẬP NHẬT UI & KHÔI PHỤC STYLE KHI CÓ HÌNH ---
    @Slot(int, object)
    def update_camera_feed(self, cam_id, frame):
        pix = self._convert_cv_to_pixmap(frame)
        error_color = "e74c3c" # Mã màu đỏ báo lỗi
        
        # 1. Chế độ 1 Camera
        if self.sess_manager.current_mode == 0 and cam_id == 1:
            # Nếu đang có lỗi (style chứa màu đỏ), reset về style mặc định
            if error_color in self.ui.camera_view_label.styleSheet():
                self.ui.camera_view_label.setStyleSheet("background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;")
            self.ui.camera_view_label.setPixmap(pix)
            
        # 2. Chế độ 2 Camera
        elif self.sess_manager.current_mode == 1:
            target_widget = None
            if cam_id == 1: target_widget = self.ui.dual_cam1_view
            elif cam_id == 2: target_widget = self.ui.dual_cam2_view
            
            if target_widget:
                # Nếu đang có lỗi, gọi update_active_border để set lại style chuẩn (Xanh nếu active, thường nếu không)
                if error_color in target_widget.styleSheet():
                    self.update_active_border(self.sess_manager.next_shot_cam_id)
                target_widget.setPixmap(pix)

    @Slot(int, int)
    def show_camera_error(self, cam_id, error_code):
        self.stop_cam(cam_id)
        msg = "MẤT KẾT NỐI\nNhấn 'Làm mới'"
        style = "background-color: #34495e; color: #e74c3c; font-weight: bold; border: 2px solid #e74c3c; font-size: 18px;"
        
        empty = QPixmap()
        if self.sess_manager.current_mode == 0 and cam_id == 1:
            self.ui.camera_view_label.setPixmap(empty)
            self.ui.camera_view_label.setText(msg)
            self.ui.camera_view_label.setStyleSheet(style)
        elif self.sess_manager.current_mode == 1:
            if cam_id == 1:
                self.ui.dual_cam1_view.setPixmap(empty); self.ui.dual_cam1_view.setText(msg)
                self.ui.dual_cam1_view.setStyleSheet(style)
            elif cam_id == 2:
                self.ui.dual_cam2_view.setPixmap(empty); self.ui.dual_cam2_view.setText(msg)
                self.ui.dual_cam2_view.setStyleSheet(style)

    @Slot(int, int, int, str)
    def update_shot_display(self, idx, num, score, text):
        if idx == 0: self.ui.score_label.setText(text)
        elif idx == 1: self.ui.dual_cam1_score.setText(text)
        elif idx == 2: self.ui.dual_cam2_score.setText(text)

    @Slot(int, list)
    def show_result_popup(self, idx, data):
        t = f"KẾT QUẢ - CAMERA {idx}" if self.sess_manager.current_mode == 1 else ""
        p = ResultPopup(data, camera_name=t, parent=self.parent_window)
        p.exec()
        self.sess_manager.reset_burst_state(idx)
        self._update_result_image(idx, QPixmap())
        self.update_shot_display(idx, 0, 0, "Điểm số: --")

    @Slot(int)
    def update_active_border(self, c):
        if self.sess_manager.current_mode == 1:
            self.ui.dual_cam1_view.set_active_border(c == 1)
            self.ui.dual_cam2_view.set_active_border(c == 2)

    def _convert_cv_to_pixmap(self, img):
        if img is None: return QPixmap()
        r = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); h, w, ch = r.shape
        return QPixmap.fromImage(QImage(r.data, w, h, ch * w, QImage.Format_RGB888))

    def reset_ui_state(self):
        empty = QPixmap()
        self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText("Chờ Camera...")
        self.ui.camera_view_label.setStyleSheet("background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;")
        self.update_active_border(1)
        for i in [0, 1, 2]:
            self.update_shot_display(i, 0, 0, "Điểm số: --")
            self._update_result_image(i, empty)

    def reset_result_display(self, idx=None):
        empty = QPixmap()
        if idx is None or idx == 0:
            self.ui.score_label.setText("Điểm số: --"); self.ui.result_image_label.setPixmap(empty)
        if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'):
            self.ui.dual_cam1_score.setText("Điểm số: --"); self.ui.dual_cam1_result_img.setPixmap(empty)
        if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'):
            self.ui.dual_cam2_score.setText("Điểm số: --"); self.ui.dual_cam2_result_img.setPixmap(empty)

    def _update_result_image(self, idx, pix):
        if idx == 0: self.ui.result_image_label.setPixmap(pix)
        elif idx == 1: self.ui.dual_cam1_result_img.setPixmap(pix)
        elif idx == 2: self.ui.dual_cam2_result_img.setPixmap(pix)

    def _get_combo(self, cam_id):
        if self.sess_manager.current_mode == 0 and cam_id == 1: return self.ui.single_cam_source
        elif self.sess_manager.current_mode == 1:
            return getattr(self.ui, 'dual_cam1_source', None) if cam_id == 1 else getattr(self.ui, 'dual_cam2_source', None)
        return None

    def set_zoom(self, c, v): self.cam_manager.set_zoom(c, v)
    
    def toggle_calib(self, c):
        active = not self.cam_manager.is_calib_mode[c]
        self.cam_manager.is_calib_mode[c] = active
        lbl = "Lưu" if active else "Hiệu chỉnh"
        cursor = Qt.CrossCursor if active else Qt.ArrowCursor
        if self.sess_manager.current_mode == 0 and c == 1:
            self.ui.calibrate_button.setText(lbl); self.ui.camera_view_label.setCursor(cursor); self.ui.camera_view_label.set_calibration_mode(active)
        elif self.sess_manager.current_mode == 1:
            if c == 1: self.ui.dual_cam1_calib.setText(lbl); self.ui.dual_cam1_view.setCursor(cursor); self.ui.dual_cam1_view.set_calibration_mode(active)
            elif c == 2: self.ui.dual_cam2_calib.setText(lbl); self.ui.dual_cam2_view.setCursor(cursor); self.ui.dual_cam2_view.set_calibration_mode(active)
    
    def set_center(self, c, p):
        view = self.ui.camera_view_label if self.sess_manager.current_mode == 0 else (self.ui.dual_cam1_view if c == 1 else self.ui.dual_cam2_view)
        self.cam_manager.set_calibration_center(c, p, (view.width(), view.height()))
        self.toggle_calib(c)
    
    def stop_cam(self, c): 
        self.cam_manager.stop_camera(c); empty = QPixmap()
        if self.sess_manager.current_mode == 0 and c == 1: 
            self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText("Đã tắt")
        elif self.sess_manager.current_mode == 1:
            if c == 1: self.ui.dual_cam1_view.setPixmap(empty); self.ui.dual_cam1_view.setText("Đã tắt")
            elif c == 2: self.ui.dual_cam2_view.setPixmap(empty); self.ui.dual_cam2_view.setText("Đã tắt")
            
    def _update_button_visibility(self): pass