# file: gui/controllers/shooting_controller.py
import os
import cv2
import logging
from collections import deque
from datetime import datetime
from PySide6.QtCore import QObject, Slot, Qt, QTimer
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage
from utils.camera import find_available_cameras
from config import APP_DATA_DIR
from gui.dialogs import ResultPopup, TraineeSessionPopup, show_warning, show_info, show_confirmation_custom
from core.saver import ImageSaver

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
        self.popup_queue = deque()
        self.is_popup_open = False 
        
        # Khởi tạo Image Saver lần đầu
        self.image_saver = ImageSaver()
        self.image_saver.start()
        
        self._connect_signals()

    def _connect_signals(self):
        self.ui.zoom_slider.valueChanged.connect(lambda v: self.set_zoom(1, v))
        self.ui.refresh_button.clicked.connect(lambda: self.on_manual_refresh(1))
        self.ui.calibrate_button.clicked.connect(lambda: self.toggle_calib(1))
        self.ui.camera_view_label.clicked.connect(lambda p: self.set_center(1, p))
        self.ui.single_cam_source.currentIndexChanged.connect(lambda i: self.change_cam_source(1, i))
        
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

    def setup_new_session(self, name, mode, soldiers):
        self.sess_manager.setup_managed_session(name, mode, soldiers)
        self.parent_window.gui.stack.setCurrentWidget(self.parent_window.gui.page_view)
        self.start_managed_practice()

    def restore_session(self, ps_id, name, mode):
        self.sess_manager.resume_managed_session(ps_id, name, mode)
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
        self.ui.back_to_dashboard_btn.setText("Kết thúc")
        self.ui.lbl_current_trainee.setVisible(not is_free)
        self.ui.btn_control_session.setVisible(False)
        
        if hasattr(self.ui, 'dual_cam1_trainee_lbl'):
            self.ui.dual_cam1_trainee_lbl.setVisible(not is_free); self.ui.dual_cam1_trainee_btn.setVisible(not is_free)
        if hasattr(self.ui, 'dual_cam2_trainee_lbl'):
            self.ui.dual_cam2_trainee_lbl.setVisible(not is_free); self.ui.dual_cam2_trainee_btn.setVisible(not is_free)
            
        self._set_trainee_btn_state(1, True); self._set_trainee_btn_state(2, True)

    def _init_camera_and_session(self):
        # --- [FIX QUAN TRỌNG] KHỞI ĐỘNG LẠI IMAGESAVER NẾU ĐÃ BỊ TẮT ---
        # Khi kết thúc phiên trước, image_saver đã bị set thành None.
        # Cần tạo lại nó để phiên mới có thể lưu ảnh.
        if self.image_saver is None:
            logger.info("ShootingController: Khởi động lại ImageSaver cho phiên mới.")
            self.image_saver = ImageSaver()
            self.image_saver.start()
        # -------------------------------------------------------------

        self.populate_camera_sources()
        self.ui.mode_selector.setCurrentIndex(0)
        self._start_cameras()
        self.trigger.activate()
        if self.sess_manager.is_free_practice: self.start_new_session(0)
        else: self.reset_result_display()
        if self.sess_manager.current_mode == 1: self.update_active_border(self.sess_manager.next_shot_cam_id)

    def show_trainee_list(self, slot=1):
        self.current_selecting_slot = slot
        data = self.sess_manager.managed_session_data
        current_ids = []
        for s_slot, s_data in self.sess_manager.active_soldiers.items():
            if s_data and s_slot != slot: current_ids.append(s_data['id'])
        current_soldier = self.sess_manager.active_soldiers.get(slot)
        if current_soldier: current_ids.append(current_soldier['id'])
        mode_str = self.sess_manager.shooting_mode
        popup = TraineeSessionPopup(data['name'], data['soldiers'], current_ids, mode_str, self.parent_window)
        popup.trainee_selected.connect(self.on_trainee_changed)
        popup.exec()

    def on_trainee_changed(self, soldier_data):
        target_slot = self.current_selecting_slot
        for slot, s in self.sess_manager.active_soldiers.items():
            if s and s['id'] == soldier_data['id'] and slot != target_slot:
                show_warning(self.parent_window, "Trùng lặp", f"Người tập {soldier_data['name']} đang tập ở Camera {slot}.")
                return
        self.sess_manager.assign_soldier_to_slot(target_slot, soldier_data)
        self.update_trainee_info_ui(target_slot, soldier_data['name'])
        s_idx = 0 if self.sess_manager.current_mode == 0 else target_slot
        self.reset_result_display(s_idx)
        self.sess_manager.start_session(s_idx)

    def update_trainee_info_ui(self, slot, name):
        text = f"Người tập: {name}"
        if slot == 1:
            if self.sess_manager.current_mode == 0: self.ui.lbl_current_trainee.setText(text)
            elif hasattr(self.ui, 'dual_cam1_trainee_lbl'): self.ui.dual_cam1_trainee_lbl.setText(text)
        elif slot == 2 and hasattr(self.ui, 'dual_cam2_trainee_lbl'): self.ui.dual_cam2_trainee_lbl.setText(text)

    def on_soldier_started(self, name): pass

    @Slot(int, list)
    def on_burst_completed(self, idx, data):
        self.popup_queue.append((idx, data))
        should_wait_others = False
        if self.sess_manager.current_mode == 1: 
            if not self.sess_manager.are_all_active_cameras_finished(): should_wait_others = True
        if should_wait_others: return 
        QTimer.singleShot(1500, self.process_popup_queue)

    def process_popup_queue(self):
        while self.popup_queue:
            idx, data = self.popup_queue.popleft()
            t = f"KẾT QUẢ - CAMERA {idx}" if self.sess_manager.current_mode == 1 else ""
            allow_retry = self.sess_manager.is_managed_session
            self.is_popup_open = True
            p = ResultPopup(data, camera_name=t, allow_retry=allow_retry, parent=self.parent_window)
            result_code = p.exec()
            self.is_popup_open = False
            target_ui_idx = 0 if self.sess_manager.current_mode == 0 else idx
            if result_code == 2 and allow_retry: 
                self.sess_manager.retry_burst(idx)
                self.reset_result_display(target_ui_idx) 
                if self.sess_manager.current_mode == 1: self.update_active_border(idx)
                return 
            if self.sess_manager.is_managed_session:
                soldier = self.sess_manager.get_soldier_at_session_idx(idx)
                if soldier: soldier['finished'] = True
                self.sess_manager.end_session(idx)
                self._set_trainee_btn_state(target_ui_idx, True)
                self.reset_result_display(target_ui_idx)
                if self.sess_manager.shooting_mode == "BURST_3" and self.sess_manager.are_all_soldiers_finished() and not self.popup_queue:
                    self.parent_window.on_auto_finish_session()
                    return
                if self.sess_manager.current_mode == 0 and not self.popup_queue: self.show_trainee_list(1)
            else:
                self.sess_manager._reset_counters(idx); self.sess_manager.reset_burst_state(idx)
                self.reset_result_display(target_ui_idx); self._set_trainee_btn_state(target_ui_idx, True)

    def stop_practice(self):
        self.trigger.deactivate()
        self.cam_manager.stop_all()
        self.sess_manager.reset_all()
        self.reset_ui_state()
        self.popup_queue.clear()
        
        # Dừng thread lưu ảnh khi thoát ra dashboard để tiết kiệm tài nguyên
        if self.image_saver: 
            self.image_saver.stop()
            self.image_saver = None 
        
        self._set_trainee_btn_state(1, True); self._set_trainee_btn_state(2, True)

    def _reset_trainee_labels(self):
        self.ui.lbl_current_trainee.setText("Người tập: --")
        if hasattr(self.ui, 'dual_cam1_trainee_lbl'): self.ui.dual_cam1_trainee_lbl.setText("Người tập: Chưa chọn")
        if hasattr(self.ui, 'dual_cam2_trainee_lbl'): self.ui.dual_cam2_trainee_lbl.setText("Người tập: Chưa chọn")

    def handle_mode_change(self, idx):
        if self.sess_manager.is_any_burst_in_progress():
            reply = show_confirmation_custom(self.parent_window, "Cảnh báo", "Đang có lượt bắn chưa hoàn thành.\nBạn có muốn hủy loạt này và chuyển chế độ không?", btn_yes_text="Đồng ý", btn_no_text="Hủy")
            if reply == "NO":
                self.ui.mode_selector.blockSignals(True); self.ui.mode_selector.setCurrentIndex(self.sess_manager.current_mode); self.ui.mode_selector.blockSignals(False); return
            else:
                for i in [0, 1, 2]:
                    if self.sess_manager.is_burst_in_progress(i): self.sess_manager.cancel_incomplete_burst(i)
        
        self.sess_manager.current_mode = idx
        self.ui.main_stack.setCurrentIndex(idx)
        self.sess_manager.reset_all()
        self.sess_manager.clear_active_soldiers() 
        self._reset_trainee_labels()
        self.popup_queue.clear()
        
        # --- [FIX CRASH] ---
        self.cam_manager.stop_all()
        QApplication.processEvents() 
        self.populate_camera_sources()
        # -------------------

        # [FIX ZOOM SYNC]
        z1 = int(self.cam_manager.zoom_levels.get(1, 1.0) * 10)
        z2 = int(self.cam_manager.zoom_levels.get(2, 1.0) * 10)
        if idx == 0: self.ui.zoom_slider.setValue(z1)
        elif idx == 1:
            if hasattr(self.ui, 'dual_cam1_zoom'): self.ui.dual_cam1_zoom.setValue(z1)
            if hasattr(self.ui, 'dual_cam2_zoom'): self.ui.dual_cam2_zoom.setValue(z2)

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
        if idx == 1: QApplication.processEvents(); self.update_active_border(self.sess_manager.next_shot_cam_id)

    def handle_shooting_mode_change(self):
        self.sess_manager.shooting_mode = self.ui.shooting_mode_selector.currentData()
        self.sess_manager.reset_all()
        self.reset_result_display()
        self.popup_queue.clear()
        if self.sess_manager.current_mode == 0: self.start_new_session(0)
        else: self.start_new_session(1); self.start_new_session(2)

    def _start_cameras(self):
        if self.sess_manager.current_mode == 0: self.cam_manager.stop_camera(2); self.cam_manager.start_camera(1)
        else: self.cam_manager.start_camera(1); self.cam_manager.start_camera(2)

    def start_new_session(self, idx):
        self.reset_result_display(idx); self.sess_manager.start_session(idx)
        self.parent_window.setFocus()
        self._set_trainee_btn_state(1, True); self._set_trainee_btn_state(2, True)

    def on_manual_refresh(self, cam_id):
        logger.info(f"Làm mới Camera {cam_id}...")
        self.cam_manager.stop_camera(cam_id)
        QApplication.processEvents()
        self.cam_manager.start_camera(cam_id)

    def populate_camera_sources(self):
        available = find_available_cameras() or [0, 1]
        combos = [self.ui.single_cam_source]
        if hasattr(self.ui, 'dual_cam1_source'): combos.extend([self.ui.dual_cam1_source, self.ui.dual_cam2_source])
        for combo in combos:
            combo.blockSignals(True)
            cur = combo.currentData(); combo.clear()
            for idx in available: combo.addItem(f"Camera {idx}", idx)
            if cur is not None:
                i = combo.findData(cur)
                if i >= 0: combo.setCurrentIndex(i)
            combo.blockSignals(False)
        self._sync_combo_selection(1); self._sync_combo_selection(2)

    def _sync_combo_selection(self, cam_id):
        combo = self._get_combo(cam_id)
        if not combo: return
        current_idx = combo.currentData()
        if current_idx is not None and current_idx != -1: self.cam_manager.cam_indices[cam_id] = current_idx

    def change_cam_source(self, cam_id, idx):
        combo = self._get_combo(cam_id)
        if combo:
            val = combo.itemData(idx)
            if val is not None: self.cam_manager.cam_indices[cam_id] = val; self.cam_manager.start_camera(cam_id)

    def _set_trainee_btn_state(self, slot, enabled):
        if self.sess_manager.current_mode == 0:
            if slot == 0 or slot == 1: self.ui.btn_select_trainee.setEnabled(enabled)
            return
        if slot == 1 and hasattr(self.ui, 'dual_cam1_trainee_btn'): self.ui.dual_cam1_trainee_btn.setEnabled(enabled)
        elif slot == 2 and hasattr(self.ui, 'dual_cam2_trainee_btn'): self.ui.dual_cam2_trainee_btn.setEnabled(enabled)

    @Slot()
    def execute_shot_logic(self):
        if self.is_popup_open: return
        if self.sess_manager.is_managed_session:
            target_cam = 1
            if self.sess_manager.current_mode == 1:
                target_cam = self.sess_manager.next_shot_cam_id
                if not self.sess_manager.active_soldiers.get(1) or not self.sess_manager.active_soldiers.get(2):
                    show_warning(self.parent_window, "Thiếu người tập", "Chế độ 2 Camera yêu cầu phải chọn đủ 2 người tập."); return 
            s_idx = 0 if self.sess_manager.current_mode == 0 else target_cam
            if not self.sess_manager.get_soldier_at_session_idx(s_idx): 
                show_warning(self.parent_window, "Chưa chọn người", "Vui lòng chọn người tập trước khi bắn."); return 

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

        if self.sess_manager.is_managed_session: self._set_trainee_btn_state(sess_idx, False)
        self.sess_manager.register_pending_shot(sess_idx)
        self.audio_manager.play_sound('shot')

        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fname = f"s{sess_idx}_cam{target_cam}_{ts}.png"
        path = os.path.join(self.save_dir, fname)
        self.parent_window.request_processing.emit(frame, center, path)

        if self.sess_manager.current_mode == 1:
            next_cam = self.sess_manager.determine_next_camera_after_shot(target_cam)
            self.sess_manager.next_shot_cam_id = next_cam
            self.update_active_border(next_cam)

    @Slot(dict)
    def on_processing_finished(self, res):
        pix = self._convert_cv_to_pixmap(res.get('result_frame'))
        score = res.get('score', 0)
        final_img_numpy = res.get('result_frame')
        save_path = res.get('image_path')
        
        # [QUAN TRỌNG] Lưu ảnh vào đĩa thông qua ImageSaver
        # Cần kiểm tra image_saver khác None vì nó có thể chưa được khởi tạo nếu không qua hàm init
        if self.sess_manager.is_managed_session and final_img_numpy is not None and save_path:
            if self.image_saver: 
                self.image_saver.save_image(final_img_numpy, save_path)
            else:
                logger.error("ImageSaver chưa khởi chạy, không thể lưu ảnh!")
        
        self.sess_manager.process_shot_result(res, pix)
        sess_idx = 0
        try:
            name = os.path.basename(res.get('image_path', ''))
            if name.startswith('s'): sess_idx = int(name.split('_')[0][1:])
        except: pass

        if self.sess_manager.is_managed_session:
            is_bursting = self.sess_manager.is_burst_in_progress(sess_idx)
            has_pending = self.sess_manager.pending_shots[sess_idx] > 0
            if not is_bursting and not has_pending:
                if self.sess_manager.shooting_mode == "SINGLE": self._set_trainee_btn_state(sess_idx, True)

        self._update_result_image(sess_idx, pix)
        is_dual_mode = (self.sess_manager.current_mode == 1)
        if score > 0: score_sound = f"score_{score}"
        else: score_sound = "miss"
        if is_dual_mode: self.audio_manager.play_sequence([f"cam{sess_idx}", score_sound])
        else: self.audio_manager.play_sound(score_sound)

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
            if error_color in target_widget.styleSheet(): self.update_active_border(self.sess_manager.next_shot_cam_id)
            target_widget.setPixmap(pix)

    @Slot(int, int)
    def show_camera_error(self, cam_id, error_code):
        self.stop_cam(cam_id); msg = "MẤT KẾT NỐI\nNhấn 'Làm mới'"; style = "background-color: #34495e; color: #e74c3c; font-weight: bold; border: 2px solid #e74c3c; font-size: 18px;"; empty = QPixmap()
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
        empty = QPixmap(); msg_wait = "Vui lòng chọn người\ntrong danh sách để bắt đầu bắn"; msg_ready = "Có thể thực hiện lượt tập"; msg_finished = "Người tập đã hoàn thành lượt bắn"
        if not self.sess_manager.is_managed_session:
            free_msg = "Ảnh kết quả sẽ hiển thị ở đây"; default_style = "font-size: 20px; font-weight: bold; color: #e74c3c;"; box_style = "background-color: #212f3d; border: 1px dashed #7f8c8d; border-radius: 8px; color: #7f8c8d; font-size: 14px;"
            if idx is None or idx == 0: self.ui.score_label.setText("Điểm số: --"); self.ui.score_label.setStyleSheet(default_style); self.ui.result_image_label.setPixmap(empty); self.ui.result_image_label.setText(free_msg); self.ui.result_image_label.setStyleSheet(box_style)
            if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'): self.ui.dual_cam1_score.setText("Điểm số: --"); self.ui.dual_cam1_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;"); self.ui.dual_cam1_result_img.setPixmap(empty); self.ui.dual_cam1_result_img.setText(free_msg); self.ui.dual_cam1_result_img.setStyleSheet(box_style)
            if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'): self.ui.dual_cam2_score.setText("Điểm số: --"); self.ui.dual_cam2_score.setStyleSheet("font-size: 16px; font-weight: bold; color: #e74c3c;"); self.ui.dual_cam2_result_img.setPixmap(empty); self.ui.dual_cam2_result_img.setText(free_msg); self.ui.dual_cam2_result_img.setStyleSheet(box_style)
            return

        def get_status_msg(slot_check):
            s_data = self.sess_manager.active_soldiers.get(slot_check)
            if not s_data: return msg_wait
            if s_data.get('finished', False): return msg_finished
            return msg_ready

        style_wait = "color: #e67e22; font-size: 18px; font-weight: bold; border: 1px dashed #e67e22;"
        style_ready = "color: #2ecc71; font-size: 18px; font-weight: bold; border: 1px solid #2ecc71;"
        style_finished = "color: #27ae60; font-size: 18px; font-weight: bold; border: 1px solid #27ae60;"
        def get_style(msg): return style_wait if msg == msg_wait else (style_finished if msg == msg_finished else style_ready)
        
        if idx is None or idx == 0: 
            self.ui.score_label.setText("Điểm số: --"); self.ui.result_image_label.setPixmap(empty)
            txt = get_status_msg(1); self.ui.result_image_label.setText(txt); self.ui.result_image_label.setStyleSheet(get_style(txt))
        if (idx is None or idx == 1) and hasattr(self.ui, 'dual_cam1_score'): 
            self.ui.dual_cam1_score.setText("Điểm số: --"); self.ui.dual_cam1_result_img.setPixmap(empty)
            txt = get_status_msg(1); self.ui.dual_cam1_result_img.setText(txt); self.ui.dual_cam1_result_img.setStyleSheet(get_style(txt))
        if (idx is None or idx == 2) and hasattr(self.ui, 'dual_cam2_score'): 
            self.ui.dual_cam2_score.setText("Điểm số: --"); self.ui.dual_cam2_result_img.setPixmap(empty)
            txt = get_status_msg(2); self.ui.dual_cam2_result_img.setText(txt); self.ui.dual_cam2_result_img.setStyleSheet(get_style(txt))

    def _update_result_image(self, idx, pix):
        default_style = "background-color: #212f3d; border: 1px solid #4a6278; border-radius: 8px;"
        if idx == 0: self.ui.result_image_label.setStyleSheet(default_style); self.ui.result_image_label.setPixmap(pix)
        elif idx == 1: self.ui.dual_cam1_result_img.setStyleSheet(default_style); self.ui.dual_cam1_result_img.setPixmap(pix)
        elif idx == 2: self.ui.dual_cam2_result_img.setStyleSheet(default_style); self.ui.dual_cam2_result_img.setPixmap(pix)

    def _get_combo(self, cam_id):
        if self.sess_manager.current_mode == 0 and cam_id == 1: return self.ui.single_cam_source
        elif self.sess_manager.current_mode == 1: return getattr(self.ui, 'dual_cam1_source', None) if cam_id == 1 else getattr(self.ui, 'dual_cam2_source', None)
        return None

    def set_zoom(self, c, v): self.cam_manager.set_zoom(c, v)
    def on_manual_refresh(self, c): 
        logger.info(f"Làm mới Camera {c}...")
        self.cam_manager.stop_camera(c)
        QApplication.processEvents()
        self.cam_manager.start_camera(c)
        
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