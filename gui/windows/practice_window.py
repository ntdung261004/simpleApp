# file: gui/windows/practice_window.py

import logging
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication, QInputDialog, QLineEdit
from PySide6.QtCore import QTimer, Signal, QThread, Slot, QPoint
import cv2
import numpy as np
import json
import shutil
import sys
import os
import time
from config import APP_DATA_DIR
from datetime import datetime
from PySide6.QtGui import QScreen, QPixmap, QFont
from PySide6.QtMultimedia import QMediaDevices

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self, worker: ProcessingWorker, trigger: BluetoothTrigger, config: dict):
        super().__init__()
        # self.config được truyền trực tiếp, không cần tải lại
        self.config = config
        labels = self.config.get("labels", {})
        app_title = labels.get("app_title", "Phần Mềm Bắn Súng")
        self.setWindowTitle(app_title)
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)
        self.gui = MainGui(self.config)
        self.setCentralWidget(self.gui)
        self.worker = worker
        self.bt_trigger = trigger
        self.active_session_id = None; self.cam = None; self.final_size = (480, 640)
        self.zoom_level = 1.0; self.calibrated_center = None; self.is_session_active = False
        self.is_camera_connected = False; self.shot_counter = 0; self.frame_read_failures = 0
        self.FRAME_FAILURE_THRESHOLD = 3
        
        self.clean_zoomed_frame_for_processing = None
        self.shot_point_on_zoomed_frame = None
        
        self.audio_manager = AudioManager(); self.video_timer = QTimer(self)
        self.db_manager = DatabaseManager()
        self.video_timer.timeout.connect(self.update_frame)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.soldier_selector.currentIndexChanged.connect(self.reset_ui_state)
        self.populate_soldier_selector(); self.reset_ui_state()

        # --- BẮT ĐẦU VÙNG SỬA ĐỔI: LẤY CAMERA INDEX TỪ CONFIG ĐÃ TẢI ---
        # Lấy camera index từ config đã được truyền vào, không đọc lại file
        try:
            self.configured_camera_index = int(self.config.get("camera_index", 0))
            logger.info(f"PracticeWindow: Sử dụng camera index = {self.configured_camera_index} từ config.")
        except (ValueError, TypeError):
            logger.warning("Giá trị camera_index trong config không hợp lệ. Dùng mặc định là 0.")
            self.configured_camera_index = 0
        # --- KẾT THÚC VÙNG SỬA ĐỔI ---
            
        self.save_dir = os.path.join(APP_DATA_DIR, "captured_images")
        os.makedirs(self.save_dir, exist_ok=True)
        logger.info(f"Thư mục lưu ảnh được thiết lập tại: {self.save_dir}")

    # ... (Các hàm update_frame, capture_photo, on_processing_finished giữ nguyên) ...
    def update_frame(self):
        if not (self.cam and self.cam.isOpened()):
            return

        ret, frame = self.cam.read()
        if not ret or frame is None:
            self.frame_read_failures += 1
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD:
                self.disconnect_camera("Mất kết nối với camera...\nVui lòng kiểm tra và nhấn 'Làm mới'.")
            return

        self.frame_read_failures = 0
        if not self.is_camera_connected:
            self.is_camera_connected = True

        processed_frame = self.crop_and_resize_frame(frame)
        if processed_frame is None: return

        self.clean_zoomed_frame_for_processing = self.apply_digital_zoom(processed_frame, self.zoom_level)

        point_to_draw = None
        h_orig, w_orig, _ = processed_frame.shape
        h_zoom, w_zoom, _ = self.clean_zoomed_frame_for_processing.shape

        if self.calibrated_center:
            cx, cy = self.calibrated_center
            start_x_on_orig = (w_orig - int(w_orig / self.zoom_level)) // 2
            start_y_on_orig = (h_orig - int(h_orig / self.zoom_level)) // 2
            
            if cx >= start_x_on_orig and cy >= start_y_on_orig:
                zoomed_cx = int((cx - start_x_on_orig) * self.zoom_level)
                zoomed_cy = int((cy - start_y_on_orig) * self.zoom_level)
                if zoomed_cx < w_zoom and zoomed_cy < h_zoom:
                    point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            point_to_draw = (w_zoom // 2, h_zoom // 2)

        self.shot_point_on_zoomed_frame = point_to_draw

        frame_to_display = self.clean_zoomed_frame_for_processing.copy()
        if self.shot_point_on_zoomed_frame:
            cv2.drawMarker(frame_to_display, self.shot_point_on_zoomed_frame, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)
        
        self.gui.display_frame(frame_to_display)

    def capture_photo(self):
        if not self.is_camera_connected:
            logger.warning("Shot blocked: Camera not connected.")
            return

        frame_for_analysis = self.clean_zoomed_frame_for_processing
        if frame_for_analysis is None:
            logger.error("Không có frame đã zoom (sạch) để phân tích.")
            return

        shot_center_for_analysis = self.shot_point_on_zoomed_frame
        
        self.audio_manager.play_sound('shot')
        
        try:
            image_to_save = self.gui.camera_view_label._pixmap.toImage()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"shot_{timestamp}.png"
            save_path = os.path.join(self.save_dir, filename)
            image_to_save.save(save_path, "PNG")
            logger.info(f"Đã lưu ảnh tại: {save_path}")

            self.request_processing.emit(frame_for_analysis, shot_center_for_analysis, save_path)
            logger.info("GUI: Đã gửi yêu cầu xử lý cho worker.")
            
        except Exception as e:
            logger.error(f"Lỗi khi đang lưu ảnh: {e}")

    @Slot(dict)
    def on_processing_finished(self, result):
        logger.info("GUI: Nhận được kết quả đã xử lý từ worker.")
        display_target_name = result.get('target_name')
        score = result.get('score')
        
        final_image_to_display = result.get('result_frame')

        if self.active_session_id is not None:
            self.shot_counter += 1
            self.db_manager.add_shot(
                session_id=self.active_session_id, shot_number=self.shot_counter, 
                score=score, target_detected=result.get('target_detected_raw'), 
                coords=result.get('coords'), image_path=result.get('image_path')
            )

        if score is not None and score > 0:
            self.audio_manager.play_score(score)
        else:
            self.audio_manager.play_sound('miss')

        self.gui.update_results(
            time_str=result.get('time_str'),
            target_name=display_target_name,
            score=score,
            result_frame=final_image_to_display
        )

    # --- HÀM load_config() ĐÃ BỊ XÓA HOÀN TOÀN ---

    # ... (Tất cả các hàm còn lại từ toggle_session trở đi giữ nguyên) ...
    def toggle_session(self):
        labels = self.config.get("labels", {}); trainee_term = labels.get("trainee", "Chiến sĩ")
        if self.is_session_active:
            shot_count = self.db_manager.get_shot_count_for_session(self.active_session_id)
            if shot_count == 0:
                msg_box = QMessageBox(self); msg_box.setWindowTitle("Xác nhận Kết thúc"); msg_box.setText("Bạn chưa thực hiện phát bắn nào.")
                msg_box.setInformativeText("Bạn có muốn kết thúc và xóa luôn phiên tập này?"); msg_box.setIcon(QMessageBox.Question)
                delete_button = msg_box.addButton("Kết thúc và Xóa", QMessageBox.DestructiveRole)
                cancel_button = msg_box.addButton("Hủy", QMessageBox.RejectRole); msg_box.exec()
                if msg_box.clickedButton() == delete_button: self.db_manager.delete_session(self.active_session_id); logger.info(f"Đã xóa phiên trống ID: {self.active_session_id}"); self.finalize_session()
                else: return
            else:
                current_soldier = self.gui.soldier_selector.currentData(); soldier_id = current_soldier['id']
                while True:
                    default_name = f"Phiên tập #{self.active_session_id}"
                    session_name, ok = QInputDialog.getText(self, "Đặt tên Phiên tập", "Nhập tên để lưu lại phiên tập này:", QLineEdit.Normal, default_name)
                    if not ok: return
                    final_name = session_name.strip() if session_name.strip() else default_name
                    if not self.db_manager.session_name_exists(final_name, soldier_id=soldier_id): self.db_manager.update_session_name(self.active_session_id, final_name); self.finalize_session(); break
                    else: QMessageBox.warning(self, "Tên bị trùng", f"{trainee_term} này đã có phiên tập tên '{final_name}'.\nVui lòng chọn một tên khác.")
        else:
            if not self.is_camera_connected: QMessageBox.warning(self, "Chưa kết nối Camera", "Vui lòng kết nối camera USB và chờ tín hiệu hiển thị trước khi bắt đầu."); return
            selected_soldier = self.gui.soldier_selector.currentData()
            if not selected_soldier:
                title = labels.get("trainee", "Thông báo"); prompt = labels.get("practice_select_trainee_first", "Vui lòng chọn một {trainee} trước khi bắt đầu.")
                message = prompt.format(trainee=trainee_term); QMessageBox.warning(self, title, message); return
            try:
                self.active_session_id = self.db_manager.create_session(selected_soldier['id'])
                if self.active_session_id:
                    self.is_session_active = True; self.shot_counter = 0; logger.info(f"Đã bắt đầu phiên tập mới. ID: {self.active_session_id} cho {trainee_term} ID: {selected_soldier['id']}")
                    self.gui.session_button.setText("KẾT THÚC"); self.gui.session_button.setObjectName("danger")
                    self.gui.style().polish(self.gui.session_button); self.gui.back_button.setEnabled(False); self.gui.soldier_selector.setEnabled(False)
            except Exception as e: logger.error(f"Không thể tạo phiên tập mới: {e}"); QMessageBox.critical(self, "Lỗi Database", "Không thể tạo phiên tập mới trong cơ sở dữ liệu.")
    def populate_soldier_selector(self):
        self.gui.soldier_selector.clear(); soldiers = self.db_manager.get_all_soldiers()
        if soldiers:
            for soldier in soldiers:
                name = soldier.get('name', 'Không tên'); class_name = soldier.get('class_name')
                display_text = f"{name}  -  {class_name}" if class_name else name; self.gui.soldier_selector.addItem(display_text, userData=soldier)
        else:
            labels = self.config.get("labels", {}); trainee_term = labels.get("trainee", "Người học")
            prompt = labels.get("practice_no_trainees_in_selector", "Chưa có {trainee} nào"); message = prompt.format(trainee=trainee_term)
            self.gui.soldier_selector.addItem(message)
    def shutdown_components(self):
        logger.info("PRACTICE: Dọn dẹp tài nguyên cục bộ..."); self.disconnect_camera()
        if self.bt_trigger: self.bt_trigger.deactivate()
        self.reset_ui_state()
    def finalize_session(self):
        self.db_manager.end_session(self.active_session_id); logger.info(f"Đã kết thúc phiên tập ID: {self.active_session_id}")
        self.is_session_active = False; self.active_session_id = None
        self.gui.session_button.setText("BẮT ĐẦU"); self.gui.session_button.setObjectName("start_button")
        self.gui.style().polish(self.gui.session_button); self.gui.back_button.setEnabled(True); self.gui.soldier_selector.setEnabled(True)
    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape; target_aspect_ratio = 3.0 / 4.0
        new_w = int(h * target_aspect_ratio); start_x = (w - new_w) // 2 if w > new_w else 0
        cropped_frame = frame[:, start_x : start_x + new_w]; return cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)
    def apply_digital_zoom(self, frame, zoom):
        if frame is None or zoom <= 1.0: return frame
        h, w, _ = frame.shape; crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2; cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating); self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")
    def set_new_center(self, click_pos: QPoint):
        widget_size = self.gui.camera_view_label.size(); img_w, img_h = self.final_size
        scale = min(widget_size.width() / img_w, widget_size.height() / img_h); display_w, display_h = int(img_w * scale), int(img_h * scale)
        offset_x, offset_y = (widget_size.width() - display_w) // 2, (widget_size.height() - display_h) // 2
        if not (offset_x <= click_pos.x() < offset_x + display_w and offset_y <= click_pos.y() < offset_y + display_h): return
        click_on_display_x = click_pos.x() - offset_x; click_on_display_y = click_pos.y() - offset_y
        click_on_zoomed_image_x = int(click_on_display_x / scale); click_on_zoomed_image_y = int(click_on_display_y / scale)
        start_x_on_original = (img_w - int(img_w / self.zoom_level)) // 2; start_y_on_original = (img_h - int(img_h / self.zoom_level)) // 2
        final_img_x = int(start_x_on_original + (click_on_zoomed_image_x / self.zoom_level)); final_img_y = int(start_y_on_original + (click_on_zoomed_image_y / self.zoom_level))
        self.calibrated_center = (final_img_x, final_img_y); logger.info(f"Đã cập nhật tâm ngắm mới (trên ảnh gốc 1x) tại: {self.calibrated_center}")
        self.toggle_calibration_mode()
    def on_zoom_changed(self, value): self.zoom_level = value / 10.0
    def connect_camera(self, index):
        self.disconnect_camera(); self.cam = Camera(index)
        if not self.cam.isOpened(): logger.error(f"PRACTICE: Không thể mở camera index {index} ở tầng driver."); self.disconnect_camera(f"Vui lòng kết nối với thiết bị camera."); return
        is_frame_read_successfully = False; attempts = 0; max_attempts = 10
        while attempts < max_attempts:
            ret, frame = self.cam.read()
            if ret and frame is not None: is_frame_read_successfully = True; break
            logger.debug(f"Đọc frame lần {attempts + 1} thất bại, thử lại sau 100ms..."); attempts += 1; time.sleep(0.1)
        if is_frame_read_successfully: self.video_timer.start(30); logger.info(f"PRACTICE: Kết nối và xác thực thành công camera index {index}.")
        else: logger.error(f"PRACTICE: Kết nối thất bại, không đọc được frame từ camera index {index} sau {max_attempts} lần thử."); self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")
    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None; self.is_camera_connected = False; self.gui.clear_video_feed(message); logger.info(f"Đã ngắt kết nối camera. Lý do: {message}")
    def refresh_camera_connection(self):
        """
        Cố gắng kết nối với camera được chỉ định trong config.
        Logic được tối ưu để không phụ thuộc vào số lượng camera.
        """
        logger.info("PRACTICE: Bắt đầu làm mới kết nối camera...")
        
        # 1. Quét để xem có camera nào khả dụng hay không.
        available_cameras = find_available_cameras()
        
        # 2. Nếu không có camera nào, dừng lại và thông báo lỗi.
        if not available_cameras:
            logger.warning("Không tìm thấy bất kỳ camera nào được kết nối.")
            self.disconnect_camera(message="Không tìm thấy camera")
            return

        # 3. Luôn thử kết nối với chỉ số camera lấy từ config.
        target_index = self.configured_camera_index
        logger.info(f"Tìm thấy {len(available_cameras)} camera. Sẽ thử kết nối với camera được cấu hình tại index: {target_index}.")
        
        # 4. Hàm connect_camera sẽ tự xử lý việc kết nối và báo lỗi nếu thất bại.
        self.connect_camera(target_index)
    def start_camera(self):
        logger.info("Màn hình luyện tập: Kích hoạt camera và trigger..."); self.populate_soldier_selector()
        if self.bt_trigger: self.bt_trigger.activate()
        if self.cam is None or not self.cam.isOpened(): self.refresh_camera_connection()
    def reset_ui_state(self):
        logger.info("Resetting Practice UI to default state."); self.gui.time_label.setText("Thời gian: --:--:--"); self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Điểm số: --"); self.gui.result_image_label.setText("Chưa có ảnh kết quả"); self.gui.result_image_label.setPixmap(QPixmap())
        self.is_session_active = False; self.active_session_id = None; self.shot_counter = 0
        self.gui.session_button.setText("BẮT ĐẦU"); self.gui.session_button.setObjectName("start_button"); self.gui.style().polish(self.gui.session_button)
        self.gui.back_button.setEnabled(True); self.gui.soldier_selector.setEnabled(True)