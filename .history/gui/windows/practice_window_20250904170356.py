# file: gui/windows/practice_window.py
import logging
from PySide6.QtWidgets import QMainWindow, QMessageBox, QApplication
from PySide6.QtCore import QTimer, Signal, QThread, Slot, QPoint
import cv2
import numpy as np
import os
from datetime import datetime
from PySide6.QtGui import QScreen, QPixmap, QFont

# THAY ĐỔI: Import cả lớp Camera
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
        # Thêm biến trạng thái cho lần bắn
        self.active_session_id = None
        # --- Thuộc tính Giao diện & Camera ---
        self.gui = MainGui()
        self.setCentralWidget(self.gui)
        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        self.calibrated_center = None
        
        # --- Các Module phụ trợ ---
        self.audio_manager = AudioManager()
        self.video_timer = QTimer(self)
        self.bt_trigger = BluetoothTrigger()
        
        self.db_manager = DatabaseManager()

        # --- Thiết lập Worker bền bỉ ---
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
        # THÊM KẾT NỐI CHO CÁC NÚT MỚI
        self.gui.session_button.clicked.connect(self.toggle_session)
        
        # --- Khởi động ---
        self.processing_thread.start()
        self.bt_trigger.start_listening()
        self.refresh_camera_connection()
        
        # Tải danh sách người dùng lên giao diện
        self.populate_soldier_selector()
        
        # ======================================================================
        # CHÚ THÍCH: THÊM VÀO LOGIC TẠO THƯ MỤC LƯU ẢNH
        # ======================================================================
        self.save_dir = "captured_images"
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            logger.info(f"Đã tạo thư mục lưu ảnh training: {self.save_dir}")
        # ======================================================================
  
    def toggle_session(self):
        """Bắt đầu hoặc kết thúc một Lần bắn."""
        # TRƯỜНГ HỢP 1: BẮT ĐẦU LẦN BẮN MỚI
        if self.active_session_id is None:
            selected_user_index = self.gui.user_selector.currentIndex()
            if selected_user_index < 0 or self.gui.user_selector.itemData(selected_user_index) is None:
                QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một người bắn.")
                return
            
            user_data = self.gui.user_selector.itemData(selected_user_index)
            user_id = user_data['id']
            
            # Tạo session mới trong DB và lưu lại ID
            session_id = self.db_manager.create_session(user_id=user_id)
            if session_id:
                self.active_session_id = session_id
                # Cập nhật giao diện
                self.gui.session_button.setText("Kết thúc Lần bắn")
                self.gui.user_selector.setEnabled(False)
                self.gui.manage_users_button.setEnabled(False)
        
        # TRƯỜNG HỢP 2: KẾT THÚC LẦN BẮN HIỆN TẠI
        else:
            self.db_manager.end_session(self.active_session_id)
            self.active_session_id = None
            # Cập nhật giao diện
            self.gui.session_button.setText("Bắt đầu Lần bắn")
            self.gui.soldier_selector.setEnabled(True)

    def populate_soldier_selector(self):
        """Lấy danh sách người lính từ DB và cập nhật vào ComboBox."""
        self.gui.soldier_selector.clear()
        soldiers = self.db_manager.get_all_soldiers()
        if soldiers:
            for soldier in soldiers:
                # Hiển thị tên, lưu trữ toàn bộ thông tin soldier vào data
                self.gui.soldier_selector.addItem(soldier['name'], soldierData=soldier)
        else:
            self.gui.soldier_selector.addItem("Chưa có người bắn")

    def update_frame(self):
        if not (self.cam and self.cam.is_opened()): return
        frame = self.cam.grab()
        if frame is None:
            self.disconnect_camera()
            return
        
        processed_frame = self.crop_and_resize_frame(frame)
        self.gui.current_frame = processed_frame.copy()
        
        zoomed_frame = self.apply_digital_zoom(processed_frame, self.zoom_level)
        
        # Logic vẽ tâm ngắm đã được đồng bộ với set_new_center
        point_to_draw = None
        if self.calibrated_center:
            # Lấy tọa độ gốc 1x
            cx, cy = self.calibrated_center
            h, w, _ = processed_frame.shape
            
            # Tính toán lại vị trí của điểm đó trên ảnh đã zoom
            start_x = (w - int(w / self.zoom_level)) // 2
            start_y = (h - int(h / self.zoom_level)) // 2
            
            # Chỉ vẽ nếu tâm ngắm nằm trong vùng nhìn thấy được sau khi zoom
            if cx >= start_x and cy >= start_y:
                zoomed_cx = int((cx - start_x) * self.zoom_level)
                zoomed_cy = int((cy - start_y) * self.zoom_level)
                if zoomed_cx < w and zoomed_cy < h:
                    point_to_draw = (zoomed_cx, zoomed_cy)
        else:
            # Tâm mặc định luôn ở giữa
            h_zoom, w_zoom, _ = zoomed_frame.shape
            point_to_draw = (w_zoom // 2, h_zoom // 2)

        if point_to_draw:
            cv2.drawMarker(zoomed_frame, point_to_draw, (0, 0, 255), cv2.MARKER_CROSS, 40, 2)

        self.gui.display_frame(zoomed_frame)
    
    def capture_photo(self):
        """
        Lưu lại frame ảnh đã zoom (không có tâm ngắm) để training, sau đó gửi đi xử lý.
        """
        # Kiểm tra xem có frame nào từ camera không
        if self.cam is None or not self.cam.is_opened():
            logger.warning("Camera chưa được kết nối hoặc đang đóng. Không thể chụp ảnh.")
            return

        # Lấy frame mới nhất trực tiếp từ camera
        # Việc này đảm bảo chúng ta có một frame hoàn toàn mới, chưa bị vẽ gì lên
        raw_frame = self.cam.grab() 
        if raw_frame is None:
            logger.warning("Không thể lấy frame từ camera. Không thể chụp ảnh.")
            return
            
        # Xử lý frame thô: crop và resize về kích thước tiêu chuẩn
        processed_frame = self.crop_and_resize_frame(raw_frame)

        # Phát âm thanh bắn
        self.audio_manager.play_sound('shot')

        # ======================================================================
        # CHÚ THÍCH: LOGIC LƯU ẢNH CHÍNH XÁC HƠN
        # ======================================================================
        try:
            # 1. Áp dụng thông số zoom hiện tại trực tiếp lên processed_frame
            #    để tạo ra ảnh cần lưu. Đảm bảo ảnh này không có dấu thập đỏ.
            image_to_save = self.apply_digital_zoom(processed_frame, self.zoom_level)

            # 2. Tạo tên file duy nhất dựa trên ngày giờ và mili giây
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"shot_{timestamp}.png"
            save_path = os.path.join(self.save_dir, filename)

            # 3. Lưu ảnh ra file
            cv2.imwrite(save_path, image_to_save)
            logger.info(f"Đã lưu ảnh để training tại: {save_path}")

        except Exception as e:
            logger.error(f"Lỗi khi đang lưu ảnh training: {e}")
        # ======================================================================

        # Gửi processed_frame đi để xử lý tính điểm như bình thường
        # (Lưu ý: worker sẽ tự áp dụng zoom nếu cần cho việc hiển thị,
        #         nhưng việc tính toán gốc là trên processed_frame này)
        self.request_processing.emit(processed_frame, self.calibrated_center, save_path)
        logger.info("GUI: Đã gửi yêu cầu xử lý cho worker.")
            
    @Slot(dict)
    def on_processing_finished(self, result):
        """
        Nhận kết quả, xử lý zoom có điều kiện và cập nhật giao diện.
        """
        logger.info("GUI: Nhận được kết quả, đang cập nhật giao diện...")

        target_name = result.get('target_name')
        score = result.get('score')
        result_frame = result.get('result_frame')
        
        # ======================================================================
        # CHÚ THÍCH: LOGIC XỬ LÝ ZOOM CÓ ĐIỀU KIỆN
        # ======================================================================
        final_image_to_display = None

        # THÊM VÀO: LƯU PHÁT BẮN VÀO DATABASE NẾU ĐANG TRONG MỘT LẦN BẮN
        if self.active_session_id is not None:
            self.db_manager.add_shot(
                session_id=self.active_session_id,
                score=result.get('score'),
                target_name=result.get('target_name'),
                coords=result.get('coords'),
                image_path=result.get('image_path')
            )

        # 1. Nếu là bắn trượt, áp dụng zoom vào ảnh frame camera
        if target_name == 'Trượt':
            final_image_to_display = self.apply_digital_zoom(result_frame, self.zoom_level)
        # 2. Nếu là bắn trúng, giữ nguyên ảnh bia gốc, không zoom
        else:
            final_image_to_display = result_frame
        # ======================================================================
        
        # Phát âm thanh tương ứng
        if score is not None and score > 0:
            self.audio_manager.play_score(score)
        else:
            self.audio_manager.play_sound('miss')

        # Cập nhật giao diện với ảnh đã được xử lý đúng
        self.gui.update_results(
            time_str=result.get('time_str'),
            target_name=target_name,
            score=score,
            result_frame=final_image_to_display
        )

    def closeEvent(self, event):
        """Dọn dẹp tài nguyên trước khi đóng ứng dụng."""
        self.video_timer.stop()
        self.bt_trigger.stop_listening()
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
        self.disconnect_camera()
        self.cam = Camera(index)
        
        # Áp dụng lại logic kiểm tra kép: Phải mở được VÀ đọc được frame
        if self.cam.isOpened() and self.cam.read()[0]:
            self.video_timer.start(30)
            logger.info(f"PRACTICE: Kết nối và xác thực thành công camera index {index}.")
        else:
            logger.error(f"PRACTICE: Kết nối thất bại, không đọc được frame từ camera index {index}.")
            self.disconnect_camera("Lỗi: Không thể lấy ảnh từ camera")

    def disconnect_camera(self, message="Vui lòng kết nối camera"):
        self.video_timer.stop()
        if self.cam:
            self.cam.release()
        self.cam = None
        self.gui.clear_video_feed(message)
    
    def refresh_camera_connection(self):
        logger.info("PRACTICE: Bắt đầu làm mới kết nối camera...")
        all_cameras = find_available_cameras()
        
        # Logic mới: Đơn giản và hiệu quả
        if all_cameras:
            # Ưu tiên camera cuối cùng trong danh sách (thường là USB)
            target_index = all_cameras[-1] 
            logger.info(f"Tìm thấy {len(all_cameras)} camera. Ưu tiên kết nối tới index {target_index}.")
            self.connect_camera(target_index)
        else:
            logger.warning("Không tìm thấy camera nào.")
            self.disconnect_camera(message="Không tìm thấy camera")
    def start_camera(self):
        """
        Khởi động camera khi màn hình này được hiển thị.
        """
        logger.info("Màn hình luyện tập đã hiển thị, bắt đầu khởi động camera...")
        # Chỉ làm mới kết nối nếu camera chưa được kết nối
        if self.cam is None or not self.cam.is_opened():
            self.refresh_camera_connection()