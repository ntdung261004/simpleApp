# file: utils/camera.py
import cv2
import logging
import sys
import time
from PySide6.QtCore import QThread, Signal, QMutex

logger = logging.getLogger(__name__)

def _get_os_backend():
    """Lấy backend camera phù hợp với hệ điều hành."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

class CameraThread(QThread):
    # Signal gửi frame (numpy array) về giao diện
    frame_received = Signal(object) 

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._is_running = True
        self.cap = None
        self.mutex = QMutex()

    def run(self):
        """Hàm chạy trong luồng riêng biệt."""
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"CAMERA THREAD: Không thể mở camera {self.index}")
            return

        # Cài đặt độ phân giải mong muốn
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        logger.info(f"CAMERA THREAD: Bắt đầu đọc camera {self.index}")

        while self._is_running:
            ret, frame = self.cap.read()
            if ret:
                # Gửi frame về giao diện thông qua Signal
                self.frame_received.emit(frame)
            else:
                # Nếu mất kết nối camera, thử lại sau một chút để tránh spam CPU
                time.sleep(0.1)
            
            # Giới hạn FPS khoảng 30-60 để không ngốn CPU quá mức (tùy chọn)
            time.sleep(0.015) 

        # Dọn dẹp khi vòng lặp kết thúc
        self.cap.release()
        logger.info(f"CAMERA THREAD: Đã dừng camera {self.index}")

    def stop(self):
        """Dừng luồng an toàn."""
        self._is_running = False
        self.quit()
        self.wait()

    def is_active(self):
        return self._is_running and self.cap is not None and self.cap.isOpened()

def find_available_cameras(max_cameras_to_check=5) -> list[int]:
    """Giữ lại hàm này để PracticeWindow sử dụng quét thiết bị."""
    logger.info("CAMERA: Bắt đầu quét các camera...")
    available_cameras = []
    api_preference = _get_os_backend()
    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras