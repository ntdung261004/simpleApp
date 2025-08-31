# main_window.py
import logging
import cv2
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtGui import QScreen

# THAY ĐỔI: Sử dụng lại pynput
from pynput import keyboard

from gui.gui import MainGui
from core.camera import Camera
from core.audio import AudioManager

logger = logging.getLogger(__name__)

# ======================================================================
# THAY ĐỔI: Quay lại sử dụng lớp BluetoothTrigger với pynput
# ======================================================================
# CHÚ THÍCH: Thay đổi trong file main_window.py


class BluetoothTrigger(QObject):
    """
    Lắng nghe sự kiện bàn phím và chỉ phát tín hiệu một lần cho mỗi lần nhấn,
    tránh việc trigger liên tục khi giữ phím.
    """
    triggered = Signal()

    def __init__(self):
        super().__init__()
        self.trigger_key = keyboard.Key.media_volume_up
        self.listener = None
        # THAY ĐỔI: Thêm biến trạng thái để theo dõi phím có đang được giữ hay không
        self._is_key_pressed = False

    def on_press(self, key):
        """Hàm được gọi khi một phím được nhấn XUỐNG."""
        # Chỉ xử lý khi đúng phím trigger và phím đó chưa được nhấn trước đó
        if key == self.trigger_key and not self._is_key_pressed:
            self._is_key_pressed = True # Đánh dấu là phím đang được giữ
            logger.info(f"Phát hiện tín hiệu trigger từ phím: {key}")
            self.triggered.emit()

    def on_release(self, key):
        """Hàm được gọi khi một phím được NHẢ RA."""
        # Nếu đúng phím trigger được nhả ra, reset lại trạng thái
        if key == self.trigger_key:
            self._is_key_pressed = False

    def start_listening(self):
        if self.listener is None:
            # THAY ĐỔI: Cung cấp cả hai hàm on_press và on_release cho Listener
            self.listener = keyboard.Listener(
                on_press=self.on_press,
                on_release=self.on_release
            )
            self.listener.start()
            logger.info(f"Bắt đầu lắng nghe tín hiệu trigger từ phím: {self.trigger_key}...")

    def stop_listening(self):
        if self.listener is not None:
            self.listener.stop()
            logger.info("Đã dừng lắng nghe tín hiệu trigger.")

def find_available_cameras(max_cameras_to_check=10):
    available_cameras = []
    for i in range(max_cameras_to_check):
        api_preference = cv2.CAP_ANY
        if sys.platform == "darwin": api_preference = cv2.CAP_AVFOUNDATION
        elif sys.platform == "win32": api_preference = cv2.CAP_DSHOW
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Phần Mềm Kiểm Tra Đường Ngắm Súng Tiểu Liên STV")
        screen = QScreen.availableGeometry(QApplication.primaryScreen())
        self.setGeometry(screen)

        self.gui = MainGui()
        self.setCentralWidget(self.gui)

        self.cam = None
        self.final_size = (480, 640)
        self.zoom_level = 1.0
        
        # CHÚ THÍCH: Khởi tạo trình quản lý âm thanh
        self.audio_manager = AudioManager()
    
        self.video_timer = QTimer(self)
        self.video_timer.timeout.connect(self.update_frame)

        # Khởi tạo và bắt đầu bộ lắng nghe trigger
        self.bt_trigger = BluetoothTrigger()
        self.bt_trigger.start_listening()
        self.bt_trigger.triggered.connect(self.capture_photo)

        # Kết nối các widget
        self.gui.calibrate_button.clicked.connect(self.capture_photo)
        self.gui.zoom_slider.valueChanged.connect(self.on_zoom_changed)
        self.gui.refresh_button.clicked.connect(self.refresh_camera_connection)

    def crop_and_resize_frame(self, frame):
        if frame is None: return None
        h, w, _ = frame.shape
        target_aspect_ratio = 3.0 / 4.0
        new_w = int(h * target_aspect_ratio)
        if w > new_w:
            start_x = (w - new_w) // 2
            cropped_frame = frame[:, start_x : start_x + new_w]
        else:
            cropped_frame = frame
        final_frame = cv2.resize(cropped_frame, self.final_size, interpolation=cv2.INTER_AREA)
        return final_frame

    def apply_digital_zoom(self, frame, zoom):
        if frame is None or zoom <= 1.0: return frame
        h, w, _ = frame.shape
        crop_w = int(w / zoom)
        crop_h = int(h / zoom)
        start_x = (w - crop_w) // 2
        start_y = (h - crop_h) // 2
        cropped = frame[start_y : start_y + crop_h, start_x : start_x + crop_w]
        zoomed_frame = cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)
        return zoomed_frame

    def refresh_camera_connection(self):
        logger.info("Người dùng yêu cầu làm mới kết nối camera...")
        all_cameras = find_available_cameras()
        target_cam_index = None
        if len(all_cameras) > 1:
            target_cam_index = 0
        if target_cam_index is not None:
            if self.cam is None or self.cam.get_index() != target_cam_index:
                self.connect_camera(target_cam_index)
        else:
            if self.cam is not None:
                self.disconnect_camera()

    def connect_camera(self, index):
        self.disconnect_camera()
        logger.info(f"Đang thử kết nối tới camera {index}...")
        self.cam = Camera(index)
        if self.cam.is_opened():
            test_frame = self.cam.grab()
            if test_frame is not None:
                logger.info(f"Kết nối thành công tới camera {index}.")
                self.video_timer.start(30)
            else:
                self.disconnect_camera()
        else:
            self.disconnect_camera()
            
    def disconnect_camera(self):
        self.video_timer.stop()
        if self.cam: self.cam.release()
        self.cam = None
        self.gui.clear_video_feed("Vui lòng kết nối camera và nhấn 'Làm mới'")

    def update_frame(self):
        if self.cam and self.cam.is_opened():
            frame = self.cam.grab()
            if frame is not None:
                processed_frame = self.crop_and_resize_frame(frame)
                zoomed_frame = self.apply_digital_zoom(processed_frame, self.zoom_level)
                h, w, _ = zoomed_frame.shape
                center_point = (w // 2, h // 2)
                color = (0, 0, 255)
                cv2.drawMarker(zoomed_frame, center_point, color, 
                               markerType=cv2.MARKER_CROSS, 
                               markerSize=40,
                               thickness=2)
                self.gui.display_frame(zoomed_frame)
            else:
                self.disconnect_camera()

    # Trong file main_window.py, bên trong lớp MainWindow

    def capture_photo(self):
        """
        Chụp lại khung hình đang hiển thị trên livestream (đã bao gồm zoom)
        và hiển thị nó ở khung kết quả.
        """
        # ======================================================================
        # THAY ĐỔI: Sử dụng self.gui.current_frame thay vì self.cam.grab()
        # self.gui.current_frame lưu trữ khung hình gốc (chưa zoom, chưa vẽ tâm)
        # ngay trước khi nó được hiển thị.
        # ======================================================================
        if self.gui.current_frame is None:
            logger.warning("Không có frame nào trên livestream để chụp.")
            return

        # 1. Lấy ảnh gốc từ livestream
        photo_frame = self.gui.current_frame.copy()

        # 2. Áp dụng chính xác mức zoom hiện tại vào ảnh vừa chụp
        zoomed_photo = self.apply_digital_zoom(photo_frame, self.zoom_level)

        # Phát âm thanh
        self.audio_manager.play_sound('shot')
        
        logger.info("Đã chụp ảnh, đang hiển thị kết quả...")
        # 3. Hiển thị ảnh đã được zoom ở khung kết quả
        self.gui.update_results(zoomed_photo)
        
    def on_zoom_changed(self, value):
        self.zoom_level = value / 10.0

    def closeEvent(self, event):
        try:
            self.video_timer.stop()
            self.bt_trigger.stop_listening()
            if self.cam:
                self.cam.release()
                logger.info("Camera đã được giải phóng.")
        except Exception as e:
            logger.exception(f"Lỗi khi đóng ứng dụng: {e}")
        super().closeEvent(event)