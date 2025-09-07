import logging
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication, QInputDialog, QLineEdit
from PySide6.QtCore import QTimer, Signal, QThread, Slot, QPoint
import cv2
import numpy as np
import os
import time
from datetime import datetime
from PySide6.QtGui import QScreen, QPixmap, QFont

from ..ui.ui_practice import MainGui
from utils.audio import AudioManager
from utils.camera import find_available_cameras, Camera
from core.triggers import BluetoothTrigger
from core.worker import ProcessingWorker
from core.database import DatabaseManager

logger = logging.getLogger(__name__)

class PracticeWindow(QMainWindow):
    request_processing = Signal(np.ndarray, object, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)
        self.active_session_id = None
        
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        self.is_session_active = False
        self.is_camera_connected = False
        self.shot_counter = 0
        # <<< THAY ĐỔI: Thêm biến đếm số lần đọc frame thất bại
        self.frame_read_failures = 0
        self.FRAME_FAILURE_THRESHOLD = 3 # Ngắt kết nối nếu đọc lỗi 3 lần liên tiếp (khoảng 0.5s)
        
        self.last_processed_frame = None
        
        # --- Các Module phụ trợ ---
        self.audio_manager = AudioManager()
        self.video_timer = QTimer(self)
        self.bt_trigger = BluetoothTrigger()
        self.db_manager = DatabaseManager()
        self.processing_thread = QThread()
        self.worker = ProcessingWorker()
        self.worker.moveToThread(self.processing_thread)

        # --- Kết nối Tín hiệu (Signals) & Tác vụ (Slots) ---
        self.request_processing.connect(self.worker.process_image)
        self.worker.finished.connect(self.on_processing_finished)
        self.processing_thread.finished.connect(self.worker.deleteLater)
        self.video_timer.timeout.connect(self.update_frame)
        self.bt_trigger.triggered.connect(self.capture_photo)
        self.gui.calibrate_button.clicked.connect(self.toggle_calibration_mode)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)
        self.gui.camera_view_label.clicked.connect(self.set_new_center)
        self.gui.session_button.clicked.connect(self.toggle_session)
        self.gui.soldier_selector.currentIndexChanged.connect(self.reset_ui_state)
        
        # --- Khởi động ---
        self.processing_thread.start()
        self.bt_trigger.start_global_listener() 
        self.populate_soldier_selector()
        self.reset_ui_state()
        
        self.save_dir = "captured_images"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            logger.info(f"Đã tạo thư mục lưu ảnh training: {self.save_dir}")
  
    def shutdown_components(self):
        """Hàm dọn dẹp khi người dùng rời khỏi màn hình này."""
        logger.info("PRACTICE: Dọn dẹp tài nguyên...")
        self.disconnect_camera()
        
        if self.bt_trigger:
            self.bt_trigger.deactivate()
            
       # if self.processing_thread:
       #     self.processing_thread.quit()
       #     self.processing_thread.wait(2000) # Chờ tối đa 2 giây
        self.reset_ui_state()

# Thay thế TOÀN BỘ hàm này trong file practice_window.py

    def toggle_session(self):
        """Bắt đầu hoặc kết thúc một phiên tập."""
        if self.is_session_active:
            # --- XỬ LÝ KẾT THÚC PHIÊN ---
            shot_count = self.db_manager.get_shot_count_for_session(self.active_session_id)

            if shot_count == 0:
                # ... (Phần xử lý phiên trống không thay đổi)
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Xác nhận Kết thúc")
                msg_box.setText("Bạn chưa thực hiện phát bắn nào.")
                msg_box.setInformativeText("Bạn có muốn kết thúc và xóa luôn phiên tập này không?")
                msg_box.setIcon(QMessageBox.Question)
                delete_button = msg_box.addButton("Kết thúc và Xóa", QMessageBox.DestructiveRole)
                cancel_button = msg_box.addButton("Hủy", QMessageBox.RejectRole)
                msg_box.exec()
                if msg_box.clickedButton() == delete_button:
                    self.db_manager.delete_session(self.active_session_id)
                    logger.info(f"Đã xóa phiên trống ID: {self.active_session_id}")
                    self.finalize_session()
                else:
                    return

            else:
                # Lấy ID của chiến sĩ đang tập luyện
                current_soldier = self.gui.soldier_selector.currentData()
                soldier_id = current_soldier['id']

                while True:
                    default_name = f"Phiên tập #{self.active_session_id}"
                    session_name, ok = QInputDialog.getText(
                        self, "Đặt tên Phiên tập", "Nhập tên để lưu lại phiên tập này:",
                        QLineEdit.Normal, default_name
                    )
                    
                    if not ok: return

                    final_name = session_name.strip() if session_name.strip() else default_name

                    # Kiểm tra tên trùng VỚI soldier_id
                    if not self.db_manager.session_name_exists(final_name, soldier_id=soldier_id):
                        self.db_manager.update_session_name(self.active_session_id, final_name)
                        self.finalize_session()
                        break
                    else:
                        QMessageBox.warning(self, "Tên bị trùng", 
                                            f"Chiến sĩ này đã có phiên tập tên '{final_name}'.\nVui lòng chọn một tên khác.")

        else:
            # --- LOGIC BẮT ĐẦU PHIÊN (KHÔNG THAY ĐỔI) ---
            # ... (Toàn bộ phần else giữ nguyên như cũ)
            if not self.is_camera_connected:
                QMessageBox.warning(self, "Chưa kết nối Camera", "Vui lòng kết nối camera USB và chờ tín hiệu hiển thị trước khi bắt đầu.")
                return
            selected_soldier = self.gui.soldier_selector.currentData()
            if not selected_soldier:
                QMessageBox.warning(self, "Chưa chọn Chiến sĩ", "Vui lòng chọn một chiến sĩ trước khi bắt đầu.")
                return
            try:
                self.active_session_id = self.db_manager.create_session(selected_soldier['id'])
                if self.active_session_id:
                    self.is_session_active = True
                    self.shot_counter = 0
                    logger.info(f"Đã bắt đầu phiên tập mới. ID: {self.active_session_id} cho chiến sĩ ID: {selected_soldier['id']}")
                    self.gui.session_button.setText("KẾT THÚC")
                    self.gui.session_button.setObjectName("danger")
                    self.gui.style().polish(self.gui.session_button)
                    self.gui.back_button.setEnabled(False)
                    self.gui.soldier_selector.setEnabled(False)
            except Exception as e:
                logger.error(f"Không thể tạo phiên tập mới: {e}")
                QMessageBox.critical(self, "Lỗi Database", "Không thể tạo phiên tập mới trong cơ sở dữ liệu.")
    def finalize_session(self):
        """Hàm riêng để dọn dẹp và reset giao diện sau khi kết thúc phiên."""
        self.db_manager.end_session(self.active_session_id)
        logger.info(f"Đã kết thúc phiên tập ID: {self.active_session_id}")
        
        self.is_session_active = False
        self.active_session_id = None
        
        self.gui.session_button.setText("BẮT ĐẦU")
        self.gui.session_button.setObjectName("start_button")
        self.gui.style().polish(self.gui.session_button)

        self.gui.back_button.setEnabled(True)
        self.gui.soldier_selector.setEnabled(True)
        
    def populate_soldier_selector(self):
        """Lấy danh sách người lính từ DB và cập nhật vào ComboBox."""
        self.gui.soldier_selector.clear()
        soldiers = self.db_manager.get_all_soldiers()
        if soldiers:
            for soldier in soldiers:
                # Hiển thị tên, lưu trữ toàn bộ thông tin soldier vào data
                self.gui.soldier_selector.addItem(soldier['name'], userData=soldier)
        else:
            self.gui.soldier_selector.addItem("Chưa có người bắn")

    def update_frame(self):
        if not (self.cam and self.cam.isOpened()):
            # Trường hợp này hiếm khi xảy ra nếu logic disconnect đã tốt
            return

        ret, frame = self.cam.read()

        # <<< THAY ĐỔI: Logic xử lý khi rút camera
        if not ret or frame is None:
            self.frame_read_failures += 1
            logger.warning(f"Không thể đọc frame, lần thất bại thứ: {self.frame_read_failures}")
            if self.frame_read_failures > self.FRAME_FAILURE_THRESHOLD:
                logger.error("Mất kết nối với camera (đọc frame thất bại nhiều lần).")
                self.disconnect_camera("Mất kết nối với camera...\nVui lòng kiểm tra kết nối và nhấn 'Làm mới'.")
            return # Thoát khỏi hàm để không xử lý frame rỗng

        # Nếu đọc thành công, reset bộ đếm lỗi
        self.frame_read_failures = 0
        
                # === TÍCH HỢP LOGIC KIỂM TRA KẾT NỐI TẠI ĐÂY ===
        # Ngay sau khi xác nhận có frame hợp lệ, chúng ta đặt cờ báo hiệu
        if not self.is_camera_connected:
            self.is_camera_connected = True
            logger.info("Camera đã kết nối thành công và sẵn sàng để bắt đầu phiên tập.")
        # ===============================================
        # Chỉ khi frame hợp lệ, chúng ta mới tiếp tục xử lý
        processed_frame = self.crop_and_resize_frame(frame)
        self.gui.current_frame = processed_frame.copy()
        zoomed_frame = self.apply_digital_zoom(processed_frame, self.zoom_level)
        
        point_to_draw = None
        if self.calibrated_center:
            cx, cy = self.calibrated_center
            h, w, _ = processed_frame.shape
            start_x = (w - int(w / self.zoom_level)) // 2
            start_y = (h - int(h / self.zoom_level)) // 2
            if cx >= start_x and cy >= start_y:
                zoomed_cx = int((cx - start_x) * self.zoom_level)
                zoomed_cy = int((cy - start_y) * self.zoom_level)
                if zoomed_cx < w and zoomed_cy < h:
                    point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            h_zoom, w_zoom, _ = zoomed_frame.shape
            point_to_draw = (w_zoom // 2, h_zoom // 2)

        if point_to_draw:
            cv2.drawMarker(zoomed_frame, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)

        # --- BẮT ĐẦU THAY ĐỔI ---
        # Lưu lại frame đã xử lý ngay trước khi hiển thị
        self.last_processed_frame = zoomed_frame.copy() 
        self.gui.display_frame(self.last_processed_frame)
        # --- KẾT THÚC THAY ĐỔI ---

    def capture_photo(self):
        """
        Lấy frame ảnh mới nhất từ camera, xử lý và gửi đi cho worker.
        """
        if not self.is_camera_connected:
            logger.warning("Shot blocked: Camera is not connected.")
            return
        # --- BẮT ĐẦU THAY ĐỔI ---
        # Sử dụng frame đã được xử lý và hiển thị gần nhất
        zoomed_photo_frame = self.last_processed_frame
        
        # Kiểm tra xem frame có tồn tại không
        if zoomed_photo_frame is None:
            logger.error("Không có frame đã xử lý để chụp khi có tín hiệu.")
            return

        # Lấy frame gốc (chưa zoom) để gửi đi phân tích
        # Vì self.gui.current_frame được cập nhật trong update_frame trước khi zoom
        processed_frame = self.gui.current_frame

        if processed_frame is None:
            logger.error("Không có frame gốc (chưa zoom) để phân tích.")
            return
        # --- KẾT THÚC THAY ĐỔI ---
            
        self.audio_manager.play_sound('shot')
        
        # Logic lưu ảnh
        try:
            # Thay vì zoom lại, ta dùng luôn ảnh đã zoom để lưu
            image_to_save = zoomed_photo_frame 
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"shot_{timestamp}.png"
            save_path = os.path.join(self.save_dir, filename)
            cv2.imwrite(save_path, image_to_save)
            logger.info(f"Đã lưu ảnh tại: {save_path}")

            # Gửi frame gốc (chưa zoom) đi để xử lý
            self.request_processing.emit(processed_frame, self.calibrated_center, save_path)
            logger.info("GUI: Đã gửi yêu cầu xử lý cho worker.")
            
        except Exception as e:
            logger.error(f"Lỗi khi đang lưu ảnh: {e}")

    @Slot(dict)
    def on_processing_finished(self, result):
        """
        Nhận kết quả cuối cùng từ worker và cập nhật giao diện.
        Toàn bộ logic xử lý ảnh (vẽ, zoom, tải bia gốc) đã được worker thực hiện.
        """
        logger.info("GUI: Nhận được kết quả đã xử lý từ worker.")

        # 1. Lấy dữ liệu đã được xử lý hoàn chỉnh từ worker
        display_target_name = result.get('target_name')
        score = result.get('score')
        final_image_to_display = result.get('result_frame') # Đây là ảnh cuối cùng để hiển thị
        
        # 2. Logic lưu vào CSDL (giữ nguyên)
        if self.active_session_id is not None:
            self.shot_counter += 1
            self.db_manager.add_shot(
                session_id=self.active_session_id,
                shot_number=self.shot_counter,
                score=score,
                # Lưu tên gốc mà model nhận diện được
                target_detected=result.get('target_detected_raw'), 
                coords=result.get('coords'),
                image_path=result.get('image_path')
            )

        # 3. Phát âm thanh (giữ nguyên)
        if score is not None and score > 0:
            self.audio_manager.play_score(score)
        else:
            self.audio_manager.play_sound('miss')

        # 4. Cập nhật giao diện với dữ liệu đã sẵn sàng
        self.gui.update_results(
            time_str=result.get('time_str'),
            target_name=display_target_name,
            score=score,
            result_frame=final_image_to_display # Hiển thị ảnh cuối cùng
        )
    def closeEvent(self, event):
        """Dọn dẹp tài nguyên trước khi đóng ứng dụng."""
        self.video_timer.stop()
        self.bt_trigger.stop_global_listener()
        self.disconnect_camera()
        
        self.db_manager.close()
        # Yêu cầu luồng nền dừng lại và chờ nó kết thúc
        self.processing_thread.quit()
        self.processing_thread.wait(3000)
        super().closeEvent(event)

    # --- Các hàm còn lại không thay đổi đáng kể ---
    def crop_and_resize_frame(self, frame):
        h, w, _ = frame.shape
        target_aspect_ratio = 3.0 / 4.0
        new_w = int(h * target_aspect_ratio)
        start_x = (w - new_w) // 2 if w > new_w else 0
        cropped_frame = frame[:, start_x : start_x + new_w]
        return cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)

    def apply_digital_zoom(self, frame, zoom):
        if zoom <= 1.0: return frame
        h, w, _ = frame.shape
        crop_w, crop_h = int(w / zoom), int(h / zoom)
        start_x, start_y = (w - crop_w) // 2, (h - crop_h) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)

    def toggle_calibration_mode(self):
        is_calibrating = not self.gui.camera_view_label._is_calibrating
        self.gui.camera_view_label.set_calibration_mode(is_calibrating)
        self.gui.calibrate_button.setText("Hủy" if is_calibrating else "Hiệu chỉnh tâm")

    def set_new_center(self, click_pos: QPoint):
        """
        Nhận tọa độ click từ GUI, tính toán ngược lại dựa trên mức zoom,
        và chuyển đổi sang tọa độ ảnh gốc một cách chính xác.
        """
        # Kích thước của widget và ảnh gốc (chưa zoom)
        widget_size = self.gui.camera_view_label.size()
        img_w, img_h = self.final_size # Ví dụ: 640, 480

        # --- Bước 1: Tìm ra kích thước và vị trí của ảnh đang được vẽ trên widget ---
        scale = min(widget_size.width() / img_w, widget_size.height() / img_h)
        display_w, display_h = int(img_w * scale), int(img_h * scale)
        offset_x, offset_y = (widget_size.width() - display_w) // 2, (widget_size.height() - display_h) // 2

        # Chỉ xử lý nếu click nằm trong vùng ảnh thật
        if not (offset_x <= click_pos.x() < offset_x + display_w and \
                offset_y <= click_pos.y() < offset_y + display_h):
            return

        # --- Bước 2: Chuyển tọa độ click trên widget thành tọa độ trên ảnh 1x (chưa zoom) ---
        # Tọa độ click tương đối so với góc trên bên trái của ảnh đang hiển thị
        click_on_display_x = click_pos.x() - offset_x
        click_on_display_y = click_pos.y() - offset_y
        
        # Tọa độ trên ảnh đã zoom (nhưng có kích thước img_w, img_h)
        click_on_zoomed_image_x = int(click_on_display_x / scale)
        click_on_zoomed_image_y = int(click_on_display_y / scale)

        # --- Bước 3: "Un-zoom" tọa độ để tìm ra tọa độ trên ảnh gốc 1x ---
        # Logic tính toán ngược lại với hàm apply_digital_zoom
        start_x_on_original = (img_w - int(img_w / self.zoom_level)) // 2
        start_y_on_original = (img_h - int(img_h / self.zoom_level)) // 2
        
        final_img_x = int(start_x_on_original + (click_on_zoomed_image_x / self.zoom_level))
        final_img_y = int(start_y_on_original + (click_on_zoomed_image_y / self.zoom_level))

        # Lưu lại tọa độ cuối cùng trên ảnh gốc 1x
        self.calibrated_center = (final_img_x, final_img_y)
        logger.info(f"Đã cập nhật tâm ngắm mới (trên ảnh gốc 1x) tại: {self.calibrated_center}")
        
        # Tự động tắt chế độ hiệu chỉnh
        self.toggle_calibration_mode()

    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0
    
    def connect_camera(self, index):
        """
        Kết nối tới camera với cơ chế thử lại để tăng độ ổn định.
        """
        self.disconnect_camera()
        self.cam = Camera(index)
        
        if not self.cam.isOpened():
            logger.error(f"PRACTICE: Không thể mở camera index {index} ở tầng driver.")
            self.disconnect_camera(f"Lỗi: Không thể mở Camera {index}")
            return

        # === LOGIC MỚI: KIÊN NHẪN THỬ LẠI ===
        is_frame_read_successfully = False
        attempts = 0
        max_attempts = 10 # Thử tối đa 10 lần
        
        while attempts < max_attempts:
            ret, frame = self.cam.read()
            if ret and frame is not None:
                is_frame_read_successfully = True
                break # Đọc thành công, thoát vòng lặp
            
            logger.debug(f"Đọc frame lần {attempts + 1} thất bại, thử lại sau 100ms...")
            attempts += 1
            time.sleep(0.1) # Chờ 100ms
        # ===================================

        if is_frame_read_successfully:
            self.video_timer.start(30)
            logger.info(f"PRACTICE: Kết nối và xác thực thành công camera index {index}.")
        else:
            logger.error(f"PRACTICE: Kết nối thất bại, không đọc được frame từ camera index {index} sau {max_attempts} lần thử.")
            self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")
            
    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        """
        Ngắt kết nối camera, dọn dẹp tài nguyên và reset lại trạng thái.
        """
        self.video_timer.stop()
        if self.cam:
            self.cam.release()
        self.cam = None

        # === THÊM DÒNG NÀY ĐỂ RESET TRẠNG THÁI ===
        self.is_camera_connected = False
        # ==========================================
        
        self.gui.clear_video_feed(message)
        logger.info(f"Đã ngắt kết nối camera. Lý do: {message}")
    
    def refresh_camera_connection(self):
        """
        Làm mới kết nối, chỉ kết nối với camera USB (index 0) khi có nhiều hơn 1 camera.
        """
        logger.info("PRACTICE: Bắt đầu làm mới kết nối camera...")
        all_cameras = find_available_cameras()
        
        # === LOGIC MỚI THEO YÊU CẦU CỦA BẠN ===
        if len(all_cameras) > 1:
            # Nếu có nhiều camera, kết nối với camera 0 (là camera USB)
            target_index = 0
            logger.info(f"Phát hiện {len(all_cameras)} camera. Kết nối với camera USB tại chỉ số {target_index}.")
            self.connect_camera(target_index)
            
        elif len(all_cameras) == 1:
            # Nếu chỉ có 1 camera, đó là camera laptop -> không kết nối
            logger.warning("Chỉ phát hiện 1 camera (laptop). Yêu cầu kết nối camera USB.")
            self.disconnect_camera(message="Vui lòng kết nối USB Camera và nhấn Làm mới")
            
        else: # len(all_cameras) == 0
            # Nếu không có camera nào
            logger.warning("Không tìm thấy camera nào.")
            self.disconnect_camera(message="Không tìm thấy camera")
    def start_camera(self):
        """
        Khởi động camera khi màn hình này được hiển thị.
        """
        logger.info("Màn hình luyện tập đã hiển thị, bắt đầu khởi động camera...")
        # Tải lại danh sách chiến sĩ mỗi khi vào màn hình
        self.populate_soldier_selector()
        # Khởi động lại trình lắng nghe nút bắn
        # Tạo mới, kết nối tín hiệu và khởi động trình lắng nghe
        if self.bt_trigger:
            self.bt_trigger.activate()
  
        # Chỉ làm mới kết nối nếu camera chưa được kết nối
        if self.cam is None or not self.cam.isOpened():
            self.refresh_camera_connection()
            
    def reset_ui_state(self):
        """Reset các thông tin trên giao diện về trạng thái mặc định."""
        logger.info("Resetting Practice UI to default state.")
        
        # Reset khu vực kết quả mới nhất
        self.gui.time_label.setText("Thời gian: --:--:--")
        self.gui.target_name_label.setText("Tên mục tiêu: --")
        self.gui.score_label.setText("Điểm số: --")
        self.gui.result_image_label.setText("Chưa có ảnh kết quả")
        self.gui.result_image_label.setPixmap(QPixmap()) # Xóa ảnh cũ
        
        # Đảm bảo các trạng thái khác cũng được reset
        self.is_session_active = False
        self.active_session_id = None
        self.shot_counter = 0
        
        # Đưa nút bấm về trạng thái ban đầu
        self.gui.session_button.setText("BẮT ĐẦU")
        self.gui.session_button.setObjectName("start_button")
        self.gui.style().polish(self.gui.session_button)
        self.gui.back_button.setEnabled(True)
        self.gui.soldier_selector.setEnabled(True)