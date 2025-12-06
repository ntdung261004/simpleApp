# file: gui/controllers/shooting_controller.py
import os
import cv2
import logging
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Qt
from PySide6.QtWidgets import QMessageBox
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
        self.ui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.ui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.ui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.ui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.ui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        self.ui.session_button.clicked.connect(lambda: self.toggle_session(0))

        if hasattr(self.ui, 'dual_cam1_session_btn'):
            self.ui.dual_cam1_session_btn.clicked.connect(lambda: self.toggle_session(1))
            self.ui.dual_cam1_zoom.valueChanged.connect(lambda v: self.set_zoom(1, v))
            self.ui.dual_cam1_refresh.clicked.connect(lambda: self.on_manual_refresh(1))
            self.ui.dual_cam1_calib.clicked.connect(lambda: self.toggle_calib(1))
            self.ui.dual_cam1_view.clicked.connect(lambda p: self.set_center(1, p))
            self.ui.dual_cam1_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
            
        if hasattr(self.ui, 'dual_cam2_session_btn'):
            self.ui.dual_cam2_session_btn.clicked.connect(lambda: self.toggle_session(2))
            self.ui.dual_cam2_zoom.valueChanged.connect(lambda v: self.set_zoom(2, v))
            self.ui.dual_cam2_refresh.clicked.connect(lambda: self.on_manual_refresh(2))
            self.ui.dual_cam2_calib.clicked.connect(lambda: self.toggle_calib(2))
            self.ui.dual_cam2_view.clicked.connect(lambda p: self.set_center(2, p))
            self.ui.dual_cam2_source.currentIndexChanged.connect(lambda i: self.change_cam_source(2, i))

        self.cam_manager.frame_received.connect(self.update_camera_feed)
        self.cam_manager.error_occurred.connect(self.show_camera_error)
        self.sess_manager.session_state_changed.connect(self.update_session_ui_state)
        self.sess_manager.shot_added.connect(self.update_shot_display)
        self.sess_manager.burst_completed.connect(self.show_result_popup)
        self.sess_manager.auto_switch_camera.connect(self.update_active_border)
        self.trigger.triggered.connect(self.execute_shot_logic)

    def start_free_practice(self):
        self.sess_manager.is_free_practice = True
        self.sess_manager.shooting_mode = "SINGLE"
        self.populate_camera_sources()
        self.ui.shooting_mode_selector.setCurrentIndex(0)
        self.ui.mode_selector.setCurrentIndex(0)
        self._start_cameras()
        self._update_button_visibility()
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
        self._start_cameras()
        self._update_button_visibility()

    def handle_shooting_mode_change(self):
        self.sess_manager.shooting_mode = self.ui.shooting_mode_selector.currentData()
        self.sess_manager.reset_all()
        self.reset_result_display()
        self._update_button_visibility()

    def _start_cameras(self):
        if self.sess_manager.current_mode == 0:
            self.cam_manager.stop_camera(2); self.cam_manager.start_camera(1)
        else:
            self.cam_manager.start_camera(1); self.cam_manager.start_camera(2)

    def toggle_session(self, idx):
        if self.sess_manager.session_active_flags[idx]: self.sess_manager.end_session(idx)
        else:
            self.reset_result_display(idx)
            self.sess_manager.start_session(idx)
            self.parent_window.setFocus()

    def populate_camera_sources(self):
        available = find_available_cameras() or [0, 1]
        combos = [self.ui.single_cam_source]
        if hasattr(self.ui, 'dual_cam1_source'): combos.extend([self.ui.dual_cam1_source, self.ui.dual_cam2_source])
        for combo in combos:
            combo.blockSignals(True)
            cur = combo.currentData()
            combo.clear()
            for idx in available: combo.addItem(f"Camera {idx}", idx)
            if cur is not None:
                i = combo.findData(cur)
                if i >= 0: combo.setCurrentIndex(i)
            combo.blockSignals(False)

    def change_cam_source(self, cam_id, idx):
        combo = self._get_combo(cam_id)
        if combo:
            val = combo.itemData(idx)
            if val is not None: self.cam_manager.cam_indices[cam_id] = val; self.cam_manager.start_camera(cam_id)

    @Slot()
    def execute_shot_logic(self):
        target_cam = 1
        if self.sess_manager.current_mode == 1:
            target_cam = self.sess_manager.next_shot_cam_id
            next_t = self.sess_manager.get_auto_switch_target(target_cam)
            if next_t == -1: return 
            if next_t: target_cam = next_t
        if not self.sess_manager.check_can_shot(target_cam): return
        frame, center = self.cam_manager.get_shot_data(target_cam)
        if frame is None: QMessageBox.warning(self.parent_window, "Lỗi", f"Camera {target_cam} mất tín hiệu."); return
        self.sess_manager.register_pending_shot(target_cam)
        self.audio_manager.play_sound('shot')
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        sess_idx = target_cam if self.sess_manager.current_mode == 1 else 0
        fname = f"s{sess_idx}_cam{target_cam}_{ts}.png"
        path = os.path.join(self.save_dir, fname)
        try:
            cv2.imwrite(path, frame)
            self.parent_window.request_processing.emit(frame, center, path)
        except Exception as e: logger.error(f"Lỗi chụp ảnh: {e}")
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

    @Slot(int, object)
    def update_camera_feed(self, cam_id, frame):
        pix = self._convert_cv_to_pixmap(frame)
        if self.sess_manager.current_mode == 0 and cam_id == 1: self.ui.camera_view_label.setPixmap(pix)
        elif self.sess_manager.current_mode == 1:
            if cam_id == 1: self.ui.dual_cam1_view.setPixmap(pix)
            elif cam_id == 2: self.ui.dual_cam2_view.setPixmap(pix)

    @Slot(int, int)
    def show_camera_error(self, cam_id, error_code):
        self.stop_cam(cam_id); msg = "MẤT KẾT NỐI"
        style = "background-color: #34495e; color: #e74c3c; font-weight: bold; border: 2px solid #e74c3c;"
        if self.sess_manager.current_mode == 0 and cam_id == 1: self.ui.camera_view_label.setText(msg); self.ui.camera_view_label.setStyleSheet(style)
        elif self.sess_manager.current_mode == 1:
            if cam_id == 1: self.ui.dual_cam1_view.setText(msg); self.ui.dual_cam1_view.setStyleSheet(style)
            elif cam_id == 2: self.ui.dual_cam2_view.setText(msg); self.ui.dual_cam2_view.setStyleSheet(style)

    @Slot(int, int, int, str)
    def update_shot_display(self, idx, num, sc, txt):
        if idx == 0: self.ui.score_label.setText(txt)
        elif idx == 1: self.ui.dual_cam1_score.setText(txt)
        elif idx == 2: self.ui.dual_cam2_score.setText(txt)

    @Slot(int, bool)
    def update_session_ui_state(self, idx, active):
        t = "KẾT THÚC" if active else "BẮT ĐẦU"; obj = "danger" if active else ""
        btn = self.ui.session_button if idx == 0 else (getattr(self.ui, 'dual_cam1_session_btn', None) if idx == 1 else getattr(self.ui, 'dual_cam2_session_btn', None))
        if btn: btn.setText(t); btn.setObjectName(obj); btn.style().polish(btn)
        any_active = any(self.sess_manager.session_active_flags.values())
        self.ui.mode_selector.setEnabled(not any_active)
        self.ui.shooting_mode_selector.setEnabled(not any_active)
        self.ui.back_to_dashboard_btn.setEnabled(not any_active)

    @Slot(int, list)
    def show_result_popup(self, idx, data):
        t = f"KẾT QUẢ - CAMERA {idx}" if self.sess_manager.current_mode == 1 else ""
        p = ResultPopup(data, camera_name=t, parent=self.parent_window)
        p.exec(); self._update_result_image(idx, QPixmap()); self.update_shot_display(idx, 0, 0, "Điểm số: --")

    @Slot(int)
    def update_active_border(self, c):
        if self.sess_manager.current_mode == 1:
            self.ui.dual_cam1_view.set_active_border(c == 1); self.ui.dual_cam2_view.set_active_border(c == 2)

    def _convert_cv_to_pixmap(self, img):
        if img is None: return QPixmap()
        r = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); h, w, ch = r.shape
        return QPixmap.fromImage(QImage(r.data, w, h, ch * w, QImage.Format_RGB888))

    def reset_ui_state(self):
        empty = QPixmap(); self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText("Chờ Camera...")
        self.update_active_border(1)
        for i in [0, 1, 2]:
            self.update_session_ui_state(i, False); self.update_shot_display(i, 0, 0, "Điểm số: --"); self._update_result_image(i, empty)

    def reset_result_display(self, idx=None):
        empty = QPixmap()
        if idx is None or idx == 0: self.ui.score_label.setText("Điểm số: --"); self.ui.result_image_label.setPixmap(empty)
        if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'): self.ui.dual_cam1_score.setText("Điểm số: --"); self.ui.dual_cam1_result_img.setPixmap(empty)
        if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'): self.ui.dual_cam2_score.setText("Điểm số: --"); self.ui.dual_cam2_result_img.setPixmap(empty)

    def _update_result_image(self, idx, pix):
        if idx == 0: self.ui.result_image_label.setPixmap(pix)
        elif idx == 1: self.ui.dual_cam1_result_img.setPixmap(pix)
        elif idx == 2: self.ui.dual_cam2_result_img.setPixmap(pix)

    def _get_combo(self, cam_id):
        if self.sess_manager.current_mode == 0 and cam_id == 1: return self.ui.single_cam_source
        elif self.sess_manager.current_mode == 1: return getattr(self.ui, 'dual_cam1_source', None) if cam_id == 1 else getattr(self.ui, 'dual_cam2_source', None)
        return None

    def set_zoom(self, c, v): self.cam_manager.set_zoom(c, v)
    def on_manual_refresh(self, c): self.cam_manager.start_camera(c)
    def toggle_calib(self, c):
        active = not self.cam_manager.is_calib_mode[c]; self.cam_manager.is_calib_mode[c] = active
        lbl = "Lưu" if active else "Hiệu chỉnh"; cursor = Qt.CrossCursor if active else Qt.ArrowCursor
        if self.sess_manager.current_mode == 0 and c == 1: self.ui.calibrate_button.setText(lbl); self.ui.camera_view_label.setCursor(cursor); self.ui.camera_view_label.set_calibration_mode(active)
        elif self.sess_manager.current_mode == 1:
            if c == 1: self.ui.dual_cam1_calib.setText(lbl); self.ui.dual_cam1_view.setCursor(cursor); self.ui.dual_cam1_view.set_calibration_mode(active)
            elif c == 2: self.ui.dual_cam2_calib.setText(lbl); self.ui.dual_cam2_view.setCursor(cursor); self.ui.dual_cam2_view.set_calibration_mode(active)
    def set_center(self, c, p):
        view = self.ui.camera_view_label if self.sess_manager.current_mode == 0 else (self.ui.dual_cam1_view if c == 1 else self.ui.dual_cam2_view)
        self.cam_manager.set_calibration_center(c, p, (view.width(), view.height()))
        self.toggle_calib(c)
    def show_camera_error(self, c, err): 
        self.stop_cam(c); msg = "MẤT KẾT NỐI"
        if self.sess_manager.current_mode == 0 and c == 1: self.ui.camera_view_label.setText(msg)
        elif self.sess_manager.current_mode == 1:
            if c == 1: self.ui.dual_cam1_view.setText(msg)
            elif c == 2: self.ui.dual_cam2_view.setText(msg)
    def stop_cam(self, c): self.cam_manager.stop_camera(c)
    def _update_button_visibility(self):
        hide = self.sess_manager.is_free_practice and self.sess_manager.shooting_mode == "SINGLE"
        def sv(b, v): 
            if b: b.setVisible(v)
        sv(self.ui.session_button, not hide)
        if hasattr(self.ui, 'dual_cam1_session_btn'): sv(self.ui.dual_cam1_session_btn, not hide)
        if hasattr(self.ui, 'dual_cam2_session_btn'): sv(self.ui.dual_cam2_session_btn, not hide)