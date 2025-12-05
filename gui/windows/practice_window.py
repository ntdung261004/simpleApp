# file: gui/windows/practice_window.py

import logging
import os
import cv2
import numpy as np
from datetime import datetime
from PySide6.QtWidgets import QMainWindow, QMessageBox, QListWidgetItem, QApplication
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtGui import QPixmap, QKeyEvent, QImage

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras
from core.database import DatabaseManager
from config import APP_DATA_DIR
from core.triggers import BluetoothTrigger
from gui.dialogs import ResultPopup, SelectSoldierDialog
from gui.managers.camera_manager import CameraManager
from gui.managers.session_manager import SessionManager

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)
    back_to_menu_signal = Signal()

    def __init__(self, worker, config: dict):
        super().__init__()
        self.config = config
        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)
        
        self.db_manager = DatabaseManager()
        self.audio_manager = AudioManager()
        self.cam_manager = CameraManager(config)
        self.sess_manager = SessionManager(self.db_manager)
        self.worker = worker
        self.bt_trigger = BluetoothTrigger()
        
        self.save_dir = os.path.join(APP_DATA_DIR, "captured_images")
        os.makedirs(self.save_dir, exist_ok=True)
        
        try: self.cam_manager.cam_indices[1] = int(self.config.get("camera_index", 0))
        except: pass

        self._connect_signals()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def start_camera(self):
        logger.info("PracticeWindow: Start (Dashboard Mode)")
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)
        self.setFocus()

    def _connect_signals(self):
        # Dashboard Navigation
        self.gui.btn_create_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))
        self.gui.btn_free_practice.clicked.connect(self.on_free_practice_clicked)
        self.gui.btn_back_main.clicked.connect(self.back_to_menu_signal.emit)
        self.gui.btn_new_session.clicked.connect(self.on_new_session_clicked)
        self.gui.btn_continue_session.clicked.connect(self.on_continue_session_clicked)
        self.gui.btn_back_dashboard_session.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_dashboard))
        
        # Create Session Page
        self.gui.list_soldiers_select.itemSelectionChanged.connect(self.update_create_session_summary)
        self.gui.cmb_session_type.currentIndexChanged.connect(self.update_create_session_summary)
        self.gui.btn_start_session.clicked.connect(self.on_confirm_create_session)
        self.gui.btn_back_create.clicked.connect(lambda: self.gui.stack.setCurrentWidget(self.gui.page_session_menu))

        # Practice View Controls
        self.gui.back_to_dashboard_btn.clicked.connect(self.on_return_to_dashboard)
        self.gui.mode_selector.currentIndexChanged.connect(self.on_change_view_mode)
        self.gui.shooting_mode_selector.currentIndexChanged.connect(self.on_change_shooting_mode_ui)
        
        self.gui.session_button.clicked.connect(lambda: self.toggle_session(0))
        self.gui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.gui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.gui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.gui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.gui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        
        # Dual Controls
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

        # Manager Signals
        self.cam_manager.frame_received.connect(self.update_camera_feed)
        self.cam_manager.error_occurred.connect(self.show_camera_error)
        self.sess_manager.session_state_changed.connect(self.update_session_ui_state)
        self.sess_manager.shot_added.connect(self.update_shot_display)
        self.sess_manager.burst_completed.connect(self.show_result_popup)
        self.sess_manager.auto_switch_camera.connect(self.update_active_border)
        self.bt_trigger.triggered.connect(self.execute_shot_logic)

    def on_free_practice_clicked(self):
        self.sess_manager.is_free_practice = True
        self.sess_manager.is_managed_session = False
        self.sess_manager.shooting_mode = "SINGLE"
        self.populate_camera_sources()
        self.gui.stack.setCurrentWidget(self.gui.page_view)
        self.gui.shooting_mode_selector.setCurrentIndex(0) 
        self.gui.mode_selector.setCurrentIndex(0)
        self._start_cameras_for_mode()
        self._update_start_button_visibility()

    def on_return_to_dashboard(self):
        self.shutdown_components()
        self.gui.stack.setCurrentWidget(self.gui.page_dashboard)

    def shutdown_components(self):
        if self.bt_trigger: self.bt_trigger.deactivate(); self.bt_trigger.stop_global_listener()
        self.cam_manager.stop_all()
        self.sess_manager.reset_all()
        self.reset_ui_state()

    # ... (Giữ nguyên các hàm logic như on_new_session_clicked, update_create_session_summary, on_confirm_create_session (placeholder), on_continue_session_clicked) ...
    def on_new_session_clicked(self):
        self.gui.list_soldiers_select.clear(); soldiers = self.db_manager.get_all_soldiers()
        for s in soldiers:
            item = QListWidgetItem(f"{s['name']} - {s.get('class_name', '')}"); item.setData(Qt.UserRole, s); self.gui.list_soldiers_select.addItem(item)
        self.gui.inp_session_name.setText(f"Phiên tập {datetime.now().strftime('%d/%m/%Y')}"); self.update_create_session_summary()
        self.gui.stack.setCurrentWidget(self.gui.page_create_session)
    def update_create_session_summary(self):
        count = len(self.gui.list_soldiers_select.selectedItems()); self.gui.lbl_sum_count.setText(f"{count} người"); self.gui.lbl_sum_type.setText(self.gui.cmb_session_type.currentText()); self.gui.lbl_sum_date.setText(datetime.now().strftime("%d/%m/%Y %H:%M"))
    def on_confirm_create_session(self):
        QMessageBox.information(self, "Thông báo", "Giao diện luyện tập theo phiên đang được xây dựng.")
    def on_continue_session_clicked(self):
        QMessageBox.information(self, "Thông báo", "Chức năng này sẽ được thực hiện ở bước sau.")

    # ... (Các hàm logic camera và session giữ nguyên từ trước) ...
    def reset_ui_state(self):
        self.gui.clear_video_feed("Chờ Camera..."); self.update_active_border(1)
        for i in [0, 1, 2]:
            self.update_session_ui_state(i, False); self.update_shot_display(i, 0, 0, "Điểm số: --")
            empty = QPixmap()
            if i == 0: self.gui.result_image_label.setPixmap(empty)
            elif i == 1 and hasattr(self.gui, 'dual_cam1_result_img'): self.gui.dual_cam1_result_img.setPixmap(empty)
            elif i == 2 and hasattr(self.gui, 'dual_cam2_result_img'): self.gui.dual_cam2_result_img.setPixmap(empty)
    
    def populate_camera_sources(self):
        available = find_available_cameras(); available = available if available else [0, 1]
        def pop_combo(combo):
            if not combo: return
            cur = combo.currentData(); combo.blockSignals(True); combo.clear()
            for idx in available: combo.addItem(f"Camera {idx}", idx)
            idx = combo.findData(cur); combo.setCurrentIndex(idx if idx >=0 else 0); combo.blockSignals(False)
        pop_combo(self.gui.single_cam_source)
        if hasattr(self.gui, 'dual_cam1_source'): pop_combo(self.gui.dual_cam1_source)
        if hasattr(self.gui, 'dual_cam2_source'): pop_combo(self.gui.dual_cam2_source)
    
    def _start_cameras_for_mode(self):
        if self.sess_manager.current_mode == 0: self.cam_manager.start_camera(1)
        else: self.cam_manager.start_camera(1); self.cam_manager.start_camera(2)

    def _update_start_button_visibility(self):
        hide = self.sess_manager.is_free_practice and self.sess_manager.shooting_mode == "SINGLE"
        def set_viz(btn, viz):
            if btn: btn.setVisible(viz)
        set_viz(self.gui.session_button, not hide)
        if hasattr(self.gui, 'dual_cam1_session_btn'): set_viz(self.gui.dual_cam1_session_btn, not hide)
        if hasattr(self.gui, 'dual_cam2_session_btn'): set_viz(self.gui.dual_cam2_session_btn, not hide)
    
    def on_change_shooting_mode_ui(self):
        mode = self.gui.shooting_mode_selector.currentData(); self.sess_manager.shooting_mode = mode; self.sess_manager.reset_all(); self._update_start_button_visibility()
    def on_change_view_mode(self, idx):
        self.sess_manager.current_mode = idx; self.gui.main_stack.setCurrentIndex(idx); self.sess_manager.reset_all(); self._start_cameras_for_mode(); self._update_start_button_visibility()
    def toggle_session(self, idx):
        if self.sess_manager.session_active_flags[idx]: self.sess_manager.end_session(idx)
        else: self.sess_manager.start_session(idx)
        self.setFocus()
    
    def set_zoom(self, c, v): self.cam_manager.set_zoom(c, v)
    def on_manual_refresh(self, c): self.populate_camera_sources(); self.cam_manager.start_camera(c)
    def toggle_calib(self, c):
        s = self.cam_manager.is_calib_mode.get(c, False); ns = not s; self.cam_manager.is_calib_mode[c] = ns
        lbl = "Lưu" if ns else "Hiệu chỉnh tâm"; cursor = Qt.CrossCursor if ns else Qt.ArrowCursor
        if self.sess_manager.current_mode == 0: self.gui.calibrate_button.setText(lbl); self.gui.camera_view_label.setCursor(cursor); self.gui.camera_view_label.set_calibration_mode(ns)
        elif self.sess_manager.current_mode == 1:
            if c==1: self.gui.dual_cam1_calib.setText(lbl); self.gui.dual_cam1_view.setCursor(cursor); self.gui.dual_cam1_view.set_calibration_mode(ns)
            else: self.gui.dual_cam2_calib.setText(lbl); self.gui.dual_cam2_view.setCursor(cursor); self.gui.dual_cam2_view.set_calibration_mode(ns)
    def set_center(self, c, p):
        sz = (self.gui.camera_view_label.width(), self.gui.camera_view_label.height()) if self.sess_manager.current_mode == 0 else ((self.gui.dual_cam1_view.width(), self.gui.dual_cam1_view.height()) if c==1 else (self.gui.dual_cam2_view.width(), self.gui.dual_cam2_view.height()))
        self.cam_manager.set_calibration_center(c, p, sz); self.toggle_calib(c)
    def change_cam_source(self, c, i):
        combo = self.gui.single_cam_source if self.sess_manager.current_mode == 0 else (getattr(self.gui, 'dual_cam1_source', None) if c==1 else getattr(self.gui, 'dual_cam2_source', None))
        if combo: self.cam_manager.cam_indices[c] = combo.itemData(i); self.cam_manager.start_camera(c)
    
    def execute_shot_logic(self):
        t = 1 if self.sess_manager.current_mode == 0 else self.sess_manager.next_shot_cam_id
        if self.sess_manager.current_mode == 1:
            nt = self.sess_manager.get_auto_switch_target(t)
            if nt == -1: return 
            if nt: t = nt
        if not self.sess_manager.check_can_shot(t): return
        fr, cen = self.cam_manager.get_shot_data(t)
        if fr is None: QMessageBox.warning(self, "Lỗi", f"Camera {t} mất tín hiệu."); return
        self.sess_manager.register_pending_shot(t); self.audio_manager.play_sound('shot')
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f"); p = os.path.join(self.save_dir, f"s{t}_{ts}.png")
        try: cv2.imwrite(p, fr); self.request_processing.emit(fr, cen, p)
        except Exception as e: logger.error(f"Lỗi lưu ảnh: {e}")
        if self.sess_manager.current_mode == 1:
            self.sess_manager.next_shot_cam_id = 2 if t == 1 else 1
            self.update_active_border(self.sess_manager.next_shot_cam_id)
    
    @Slot(dict)
    def on_processing_finished(self, res):
        pix = self._convert_cv_to_pixmap(res.get('result_frame')); sc = res.get('score', 0)
        idx = 0
        try: nm = os.path.basename(res.get('image_path')); idx = int(nm[1:].split('_')[0]) if nm.startswith('s') else 0
        except: pass
        if idx==0: self.gui.result_image_label.setPixmap(pix)
        elif idx==1 and hasattr(self.gui, 'dual_cam1_result_img'): self.gui.dual_cam1_result_img.setPixmap(pix)
        elif idx==2 and hasattr(self.gui, 'dual_cam2_result_img'): self.gui.dual_cam2_result_img.setPixmap(pix)
        if sc > 0: self.audio_manager.play_score(sc)
        else: self.audio_manager.play_sound('miss')
        self.sess_manager.process_shot_result(res)
    
    @Slot(int, object)
    def update_camera_feed(self, c, f):
        p = self._convert_cv_to_pixmap(f)
        if self.sess_manager.current_mode == 0 and c==1: self.gui.camera_view_label.setPixmap(p)
        elif self.sess_manager.current_mode == 1:
            if c==1 and hasattr(self.gui, 'dual_cam1_view'): self.gui.dual_cam1_view.setPixmap(p)
            elif c==2 and hasattr(self.gui, 'dual_cam2_view'): self.gui.dual_cam2_view.setPixmap(p)
    @Slot(int, int)
    def show_camera_error(self, c, e):
        msg = "MẤT KẾT NỐI"
        if self.sess_manager.current_mode == 0:
             if c == 1: self.gui.camera_view_label.setText(msg)
        else:
             if c == 1: self.gui.dual_cam1_view.setText(msg)
             elif c == 2: self.gui.dual_cam2_view.setText(msg)
    @Slot(int, int, int, str)
    def update_shot_display(self, idx, num, sc, txt):
        if idx == 0: self.gui.score_label.setText(txt)
        elif idx == 1: self.gui.dual_cam1_score.setText(txt)
        elif idx == 2: self.gui.dual_cam2_score.setText(txt)
    @Slot(int, bool)
    def update_session_ui_state(self, idx, active):
        t = "KẾT THÚC" if active else "BẮT ĐẦU"; o = "danger" if active else ""
        b = self.gui.session_button if idx == 0 else (getattr(self.gui, 'dual_cam1_session_btn', None) if idx == 1 else getattr(self.gui, 'dual_cam2_session_btn', None))
        if b: b.setText(t); b.setObjectName(o); b.style().polish(b)
    @Slot(int, list)
    def show_result_popup(self, idx, data):
        t = f"KẾT QUẢ CAM {idx}" if self.sess_manager.current_mode == 1 else ""
        p = ResultPopup(data, camera_name=t, parent=self); p.exec()
        e = QPixmap()
        if idx == 0: self.gui.score_label.setText("--"); self.gui.result_image_label.setPixmap(e)
        elif idx == 1: self.gui.dual_cam1_score.setText("--"); self.gui.dual_cam1_result_img.setPixmap(e)
        elif idx == 2: self.gui.dual_cam2_score.setText("--"); self.gui.dual_cam2_result_img.setPixmap(e)
    @Slot(int)
    def update_active_border(self, c):
        if self.sess_manager.current_mode == 1:
            self.gui.dual_cam1_view.set_active_border(c == 1); self.gui.dual_cam2_view.set_active_border(c == 2)
    def _convert_cv_to_pixmap(self, i):
        if i is None: return QPixmap()
        r = cv2.cvtColor(i, cv2.COLOR_BGR2RGB); h, w, ch = r.shape
        return QPixmap.fromImage(QImage(r.data, w, h, ch * w, QImage.Format_RGB888))
    def keyPressEvent(self, e):
        if e.key() in [Qt.Key_Enter, Qt.Key_Return]: e.accept(); self.execute_shot_logic()
        else: super().keyPressEvent(e)
    def mousePressEvent(self, e): self.setFocus(); super().mousePressEvent(e)