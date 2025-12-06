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
from gui.dialogs import ResultPopup, TraineeSessionPopup

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
        self.current_selecting_slot = 1 
        self._connect_signals()

    def _connect_signals(self):
        self.ui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.ui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.ui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.ui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.ui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        
        self.ui.btn_select_trainee.clicked.connect(lambda: self.show_trainee_list(1))
        self.ui.btn_save_session.clicked.connect(self.save_and_exit_managed_session)
        self.ui.btn_back_header.clicked.connect(self.stop_practice_and_return)

        if hasattr(self.ui, 'dual_cam1_view'):
            self.ui.dual_cam1_zoom.valueChanged.connect(lambda v: self.set_zoom(1, v))
            self.ui.dual_cam1_refresh.clicked.connect(lambda: self.on_manual_refresh(1))
            self.ui.dual_cam1_calib.clicked.connect(lambda: self.toggle_calib(1))
            self.ui.dual_cam1_view.clicked.connect(lambda p: self.set_center(1, p))
            self.ui.dual_cam1_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
            if hasattr(self.ui, 'dual_cam1_trainee_btn'):
                self.ui.dual_cam1_trainee_btn.clicked.connect(lambda: self.show_trainee_list(1))
            
        if hasattr(self.ui, 'dual_cam2_view'):
            self.ui.dual_cam2_zoom.valueChanged.connect(lambda v: self.set_zoom(2, v))
            self.ui.dual_cam2_refresh.clicked.connect(lambda: self.on_manual_refresh(2))
            self.ui.dual_cam2_calib.clicked.connect(lambda: self.toggle_calib(2))
            self.ui.dual_cam2_view.clicked.connect(lambda p: self.set_center(2, p))
            self.ui.dual_cam2_source.currentIndexChanged.connect(lambda i: self.change_cam_source(2, i))
            if hasattr(self.ui, 'dual_cam2_trainee_btn'):
                self.ui.dual_cam2_trainee_btn.clicked.connect(lambda: self.show_trainee_list(2))

        self.cam_manager.frame_received.connect(self.update_camera_feed)
        self.cam_manager.error_occurred.connect(self.show_camera_error)
        
        self.sess_manager.session_state_changed.connect(self.update_session_ui_state)
        self.sess_manager.shot_added.connect(self.update_shot_display)
        self.sess_manager.burst_completed.connect(self.on_burst_completed)
        self.sess_manager.auto_switch_camera.connect(self.update_active_border)
        self.sess_manager.soldier_session_started.connect(self.on_soldier_started)

        self.trigger.triggered.connect(self.execute_shot_logic)

    def start_free_practice(self):
        self.sess_manager.is_free_practice = True
        self.sess_manager.is_managed_session = False
        self._setup_ui_for_mode("FREE")
        self._init_camera_and_session()

    def initialize_managed_session(self, name, mode, soldiers):
        self.sess_manager.setup_managed_session(name, mode, soldiers)
        self.parent_window.gui.stack.setCurrentWidget(self.parent_window.gui.page_view)
        self.start_managed_practice()

    def start_managed_practice(self):
        self.sess_manager.is_free_practice = False
        self.sess_manager.is_managed_session = True
        self._setup_ui_for_mode("MANAGED")
        self._init_camera_and_session()

    def _setup_ui_for_mode(self, mode):
        is_free = (mode == "FREE")
        self.ui.lbl_session_info.setText("LUYỆN TẬP TỰ DO" if is_free else f"PHIÊN: {self.sess_manager.managed_session_data.get('name', '').upper()}")
        self.ui.lbl_mode_prompt.setVisible(is_free)
        self.ui.shooting_mode_selector.setVisible(is_free)
        self.ui.lbl_shooting_mode_fixed.setVisible(not is_free)
        if not is_free:
            mode_text = "Bắn loạt (3 viên)" if self.sess_manager.shooting_mode == "BURST_3" else "Bắn từng viên"
            self.ui.lbl_shooting_mode_fixed.setText(mode_text)

        if self.sess_manager.current_mode == 0:
            self.ui.btn_select_trainee.setVisible(not is_free)
        else:
            self.ui.btn_select_trainee.setVisible(False)
            
        self.ui.btn_save_session.setVisible(not is_free)
        self.ui.back_to_dashboard_btn.setText("Kết thúc" if is_free else "Thoát phiên")
        self.ui.lbl_current_trainee.setVisible(not is_free)
        self.ui.btn_control_session.setVisible(False)
        
        if hasattr(self.ui, 'dual_cam1_trainee_lbl'):
            self.ui.dual_cam1_trainee_lbl.setVisible(not is_free)
            self.ui.dual_cam1_trainee_btn.setVisible(not is_free)
        if hasattr(self.ui, 'dual_cam2_trainee_lbl'):
            self.ui.dual_cam2_trainee_lbl.setVisible(not is_free)
            self.ui.dual_cam2_trainee_btn.setVisible(not is_free)

    def _init_camera_and_session(self):
        self.populate_camera_sources()
        self.ui.mode_selector.setCurrentIndex(0)
        self._start_cameras()
        self.trigger.activate()
        if self.sess_manager.is_free_practice:
             self.start_new_session(0)
        else:
            self.reset_result_display()
        
        if self.sess_manager.current_mode == 1:
            self.update_active_border(self.sess_manager.next_shot_cam_id)

    def stop_practice_and_return(self):
        self.stop_practice()
        self.parent_window.gui.stack.setCurrentWidget(self.parent_window.gui.page_dashboard)

    def show_trainee_list(self, slot=1):
        self.current_selecting_slot = slot
        data = self.sess_manager.managed_session_data
        
        current_ids = []
        for s_slot, s_data in self.sess_manager.active_soldiers.items():
            if s_data and s_slot != slot:
                current_ids.append(s_data['id'])
        
        current_soldier = self.sess_manager.active_soldiers.get(slot)
        if current_soldier:
            current_ids.append(current_soldier['id'])
            
        mode_str = self.sess_manager.shooting_mode
        popup = TraineeSessionPopup(data['name'], data['soldiers'], current_ids, mode_str, self.parent_window)
        popup.trainee_selected.connect(self.on_trainee_changed)
        popup.exec()

    def on_trainee_changed(self, soldier_data):
        target_slot = self.current_selecting_slot
        
        for slot, s in self.sess_manager.active_soldiers.items():
            if s and s['id'] == soldier_data['id'] and slot != target_slot:
                QMessageBox.warning(self.parent_window, "Trùng lặp", f"Chiến sĩ {soldier_data['name']} đang tập ở Camera {slot}.")
                return

        self.sess_manager.assign_soldier_to_slot(target_slot, soldier_data)
        self.update_trainee_info_ui(target_slot, soldier_data['name'])
        
        s_idx = 0 if self.sess_manager.current_mode == 0 else target_slot
        
        self.reset_result_display(s_idx)
        self.sess_manager.start_session(s_idx)

    def update_trainee_info_ui(self, slot, name):
        text = f"Người tập: {name}"
        if slot == 1:
            if self.sess_manager.current_mode == 0:
                self.ui.lbl_current_trainee.setText(text)
            elif hasattr(self.ui, 'dual_cam1_trainee_lbl'):
                self.ui.dual_cam1_trainee_lbl.setText(text)
        elif slot == 2 and hasattr(self.ui, 'dual_cam2_trainee_lbl'):
             self.ui.dual_cam2_trainee_lbl.setText(text)

    def toggle_managed_turn(self): pass
    def on_soldier_started(self, name): pass

    def save_and_exit_managed_session(self):
        self.stop_practice()
        self.parent_window.gui.stack.setCurrentWidget(self.parent_window.gui.page_dashboard)

    @Slot(int, list)
    def on_burst_completed(self, idx, data):
        t = f"KẾT QUẢ - CAMERA {idx}" if self.sess_manager.current_mode == 1 else ""
        
        # --- FIX: Tách biệt logic Popup cho Free và Managed ---
        allow_retry = self.sess_manager.is_managed_session
        p = ResultPopup(data, camera_name=t, allow_retry=allow_retry, parent=self.parent_window)
        result_code = p.exec()
        
        target_ui_idx = 0 if self.sess_manager.current_mode == 0 else idx
        
        if result_code == 2 and allow_retry: # Bắn lại (chỉ Managed)
            self.sess_manager.retry_burst(idx)
            self.reset_result_display(target_ui_idx)
            return

        if self.sess_manager.is_managed_session:
            soldier = self.sess_manager.get_soldier_at_session_idx(idx)
            if soldier: soldier['finished'] = True
            self.sess_manager.end_session(idx)
            self.reset_result_display(target_ui_idx)
            self.show_trainee_list(target_ui_idx if self.sess_manager.current_mode == 1 else 1)
        else:
            # Free Mode: Reset bộ đếm để loạt sau bắn từ 1
            self.sess_manager._reset_counters(idx) 
            self.sess_manager.reset_burst_state(idx)
            self._update_result_image(idx, QPixmap())
            self.update_shot_display(idx, 0, 0, "Điểm số: --")

    def stop_practice(self):
        self.trigger.deactivate()
        self.cam_manager.stop_all()
        self.sess_manager.reset_all()
        self.reset_ui_state()

    def _reset_trainee_labels(self):
        self.ui.lbl_current_trainee.setText("Người tập: --")
        if hasattr(self.ui, 'dual_cam1_trainee_lbl'):
            self.ui.dual_cam1_trainee_lbl.setText("Người tập: Chưa chọn")
        if hasattr(self.ui, 'dual_cam2_trainee_lbl'):
            self.ui.dual_cam2_trainee_lbl.setText("Người tập: Chưa chọn")

    def handle_mode_change(self, idx):
        if self.sess_manager.is_any_burst_in_progress():
            reply = QMessageBox.warning(
                self.parent_window, "Cảnh báo",
                "Đang có lượt bắn chưa hoàn thành (loạt 3 viên).\n"
                "Bạn có muốn hủy loạt bắn này và chuyển chế độ không?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                self.ui.mode_selector.blockSignals(True)
                self.ui.mode_selector.setCurrentIndex(self.sess_manager.current_mode)
                self.ui.mode_selector.blockSignals(False)
                return
            else:
                for i in [0, 1, 2]:
                    if self.sess_manager.is_burst_in_progress(i):
                        self.sess_manager.cancel_incomplete_burst(i)
        
        self.sess_manager.current_mode = idx
        self.ui.main_stack.setCurrentIndex(idx)
        
        self.sess_manager.reset_all()
        self.sess_manager.clear_active_soldiers() 
        self._reset_trainee_labels()
        
        self.populate_camera_sources()
        if idx == 1:
            if self.cam_manager.cam_indices[1] == self.cam_manager.cam_indices[2]:
                available = find_available_cameras()
                if len(available) >= 2:
                    new_idx = available[1] if available[0] == self.cam_manager.cam_indices[1] else available[0]
                    self.cam_manager.cam_indices[2] = new_idx
                    self._sync_combo_selection(2)
        self._start_cameras()
        self._setup_ui_for_mode("MANAGED" if self.sess_manager.is_managed_session else "FREE")
        
        self.reset_result_display()

        if self.sess_manager.is_free_practice:
            if idx == 0: self.start_new_session(0)
            else: self.start_new_session(1); self.start_new_session(2)
        else:
            if idx == 1: self.update_active_border(self.sess_manager.next_shot_cam_id)

    def handle_shooting_mode_change(self):
        self.sess_manager.shooting_mode = self.ui.shooting_mode_selector.currentData()
        self.sess_manager.reset_all()
        self.reset_result_display()
        if self.sess_manager.current_mode == 0: self.start_new_session(0)
        else: self.start_new_session(1); self.start_new_session(2)

    def _start_cameras(self):
        if self.sess_manager.current_mode == 0:
            self.cam_manager.stop_camera(2); self.cam_manager.start_camera(1)
        else:
            self.cam_manager.start_camera(1); self.cam_manager.start_camera(2)

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
            if val is not None: self.cam_manager.cam_indices[cam_id] = val; self.cam_manager.start_camera(cam_id)

    @Slot()
    def execute_shot_logic(self):
        if self.sess_manager.is_managed_session:
            target_cam = 1
            if self.sess_manager.current_mode == 1:
                target_cam = self.sess_manager.next_shot_cam_id
                
            s_idx = 0 if self.sess_manager.current_mode == 0 else target_cam
            soldier = self.sess_manager.get_soldier_at_session_idx(s_idx)
            
            if not soldier:
                return 

        target_cam = 1
        if self.sess_manager.current_mode == 1:
            target_cam = self.sess_manager.next_shot_cam_id
            next_t = self.sess_manager.get_auto_switch_target(target_cam)
            if next_t == -1: return 
            if next_t: target_cam = next_t

        sess_idx = 0 if self.sess_manager.current_mode == 0 else target_cam
        if not self.sess_manager.check_can_shot(sess_idx): return

        if not self.cam_manager.is_camera_ready(target_cam): return

        frame, center = self.cam_manager.get_shot_data(target_cam)
        if frame is None: return

        self.sess_manager.register_pending_shot(sess_idx)
        self.audio_manager.play_sound('shot')

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fname = f"s{sess_idx}_cam{target_cam}_{ts}.png"
        path = os.path.join(self.save_dir, fname)
        try:
            cv2.imwrite(path, frame)
            self.parent_window.request_processing.emit(frame, center, path)
        except Exception as e:
            logger.error(f"Lỗi chụp ảnh: {e}")
            self.sess_manager.rollback_pending_shot(sess_idx)

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
        error_color = "e74c3c"
        if self.sess_manager.current_mode == 0 and cam_id == 1:
            if error_color in self.ui.camera_view_label.styleSheet():
                self.ui.camera_view_label.setStyleSheet("background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;")
            self.ui.camera_view_label.setPixmap(pix)
        elif self.sess_manager.current_mode == 1:
            target_widget = self.ui.dual_cam1_view if cam_id == 1 else self.ui.dual_cam2_view
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
            self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText(msg); self.ui.camera_view_label.setStyleSheet(style)
        elif self.sess_manager.current_mode == 1:
            if cam_id == 1: self.ui.dual_cam1_view.setPixmap(empty); self.ui.dual_cam1_view.setText(msg); self.ui.dual_cam1_view.setStyleSheet(style)
            elif cam_id == 2: self.ui.dual_cam2_view.setPixmap(empty); self.ui.dual_cam2_view.setText(msg); self.ui.dual_cam2_view.setStyleSheet(style)

    @Slot(int, int, int, str)
    def update_shot_display(self, idx, num, score, text):
        if idx == 0: self.ui.score_label.setText(text)
        elif idx == 1: self.ui.dual_cam1_score.setText(text)
        elif idx == 2: self.ui.dual_cam2_score.setText(text)

    @Slot(int, bool)
    def update_session_ui_state(self, idx, active): pass

    def update_active_border(self, c):
        if self.sess_manager.current_mode == 1:
            self.ui.dual_cam1_view.set_active_border(c == 1); self.ui.dual_cam2_view.set_active_border(c == 2)

    def _convert_cv_to_pixmap(self, img):
        if img is None: return QPixmap()
        r = cv2.cvtColor(img, cv2.COLOR_BGR2RGB); h, w, ch = r.shape
        return QPixmap.fromImage(QImage(r.data, w, h, ch * w, QImage.Format_RGB888))

    def reset_ui_state(self):
        empty = QPixmap(); self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText("Chờ Camera...")
        self.ui.camera_view_label.setStyleSheet("background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px; color: #95a5a6;")
        self.update_active_border(1)
        for i in [0, 1, 2]: self.update_shot_display(i, 0, 0, "Điểm số: --"); self._update_result_image(i, empty)

    def reset_result_display(self, idx=None):
        empty = QPixmap()
        msg_wait = "Vui lòng chọn người\ntrong danh sách để bắt đầu bắn"
        msg_ready = "Có thể thực hiện lượt tập"
        
        # --- FIX: Placeholder cho Free Practice ---
        if not self.sess_manager.is_managed_session:
            free_msg = "Ảnh kết quả sẽ hiển thị ở đây"
            default_style = "font-size: 20px; font-weight: bold; color: #e74c3c;"
            box_style = "background-color: #212f3d; border: 1px dashed #7f8c8d; border-radius: 8px; color: #7f8c8d; font-size: 14px;"
            
            if idx is None or idx == 0:
                self.ui.score_label.setText("Điểm số: --")
                self.ui.score_label.setStyleSheet(default_style)
                self.ui.result_image_label.setPixmap(empty)
                self.ui.result_image_label.setText(free_msg) 
                self.ui.result_image_label.setStyleSheet(box_style)
            
            if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'):
                self.ui.dual_cam1_score.setText("Điểm số: --")
                self.ui.dual_cam1_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
                self.ui.dual_cam1_result_img.setPixmap(empty)
                self.ui.dual_cam1_result_img.setText(free_msg)
                self.ui.dual_cam1_result_img.setStyleSheet(box_style)

            if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'):
                self.ui.dual_cam2_score.setText("Điểm số: --")
                self.ui.dual_cam2_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;")
                self.ui.dual_cam2_result_img.setPixmap(empty)
                self.ui.dual_cam2_result_img.setText(free_msg)
                self.ui.dual_cam2_result_img.setStyleSheet(box_style)
            return
        # ------------------------------------------

        def get_status_msg(slot_check):
            s_data = self.sess_manager.active_soldiers.get(slot_check)
            if s_data: return msg_ready
            return msg_wait

        style_wait = "color: #e67e22; font-size: 18px; font-weight: bold; border: 1px dashed #e67e22;"
        style_ready = "color: #2ecc71; font-size: 18px; font-weight: bold; border: 1px solid #2ecc71;" # Xanh lá
        
        if idx is None or idx == 0: 
            self.ui.score_label.setText("Điểm số: --")
            self.ui.result_image_label.setPixmap(empty)
            txt = get_status_msg(1)
            self.ui.result_image_label.setText(txt)
            self.ui.result_image_label.setStyleSheet(style_ready if txt == msg_ready else style_wait)
        
        if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'): 
            self.ui.dual_cam1_score.setText("Điểm số: --")
            self.ui.dual_cam1_result_img.setPixmap(empty)
            txt = get_status_msg(1)
            self.ui.dual_cam1_result_img.setText(txt)
            self.ui.dual_cam1_result_img.setStyleSheet(style_ready if txt == msg_ready else style_wait)

        if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'): 
            self.ui.dual_cam2_score.setText("Điểm số: --")
            self.ui.dual_cam2_result_img.setPixmap(empty)
            txt = get_status_msg(2)
            self.ui.dual_cam2_result_img.setText(txt)
            self.ui.dual_cam2_result_img.setStyleSheet(style_ready if txt == msg_ready else style_wait)

    def _update_result_image(self, idx, pix):
        default_style = "background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px;"
        
        if idx == 0: 
            self.ui.result_image_label.setStyleSheet(default_style)
            self.ui.result_image_label.setPixmap(pix)
        elif idx == 1: 
            self.ui.dual_cam1_result_img.setStyleSheet(default_style)
            self.ui.dual_cam1_result_img.setPixmap(pix)
        elif idx == 2: 
            self.ui.dual_cam2_result_img.setStyleSheet(default_style)
            self.ui.dual_cam2_result_img.setPixmap(pix)

    def _get_combo(self, cam_id):
        if self.sess_manager.current_mode == 0 and cam_id == 1: return self.ui.single_cam_source
        elif self.sess_manager.current_mode == 1: return getattr(self.ui, 'dual_cam1_source', None) if cam_id == 1 else getattr(self.ui, 'dual_cam2_source', None)
        return None

    def set_zoom(self, c, v): self.cam_manager.set_zoom(c, v)
    def on_manual_refresh(self, c): self.cam_manager.stop_camera(c); QApplication.processEvents(); self.populate_camera_sources(); self.cam_manager.start_camera(c)
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
    def stop_cam(self, c): 
        self.cam_manager.stop_camera(c); empty = QPixmap()
        if self.sess_manager.current_mode == 0 and c == 1: self.ui.camera_view_label.setPixmap(empty); self.ui.camera_view_label.setText("Đã tắt")
        elif self.sess_manager.current_mode == 1:
            if c == 1: self.ui.dual_cam1_view.setPixmap(empty); self.ui.dual_cam1_view.setText("Đã tắt")
            elif c == 2: self.ui.dual_cam2_view.setPixmap(empty); self.ui.dual_cam2_view.setText("Đã tắt")
    def _update_button_visibility(self): pass