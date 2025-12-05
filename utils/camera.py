# file: utils/camera.py
import cv2
import logging
import sys
import time
from PySide6.QtCore import QThread, Signal, QMutex

logger = logging.getLogger(__name__)

def _get_os_backend():
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

class CameraThread(QThread):
    frame_received = Signal(object)
    error_occurred = Signal(int)

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._is_running = True
        self.cap = None
        self.consecutive_failures = 0
        # Ngưỡng lỗi: 10 frame liên tiếp (~0.3s)
        self.FAILURE_THRESHOLD = 10 

    def run(self):
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"CAMERA {self.index}: Không thể mở thiết bị.")
            self.error_occurred.emit(self.index)
            return

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        logger.info(f"CAMERA {self.index}: Bắt đầu stream.")

        while self._is_running:
            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    self.consecutive_failures = 0
                    self.frame_received.emit(frame)
                else:
                    self.consecutive_failures += 1
                    if self.consecutive_failures >= self.FAILURE_THRESHOLD:
                        logger.error(f"Cam {self.index}: MẤT TÍN HIỆU.")
                        self.error_occurred.emit(self.index)
                        break 
                    
                    # QUAN TRỌNG: Thêm sleep để tránh ngốn CPU khi chờ/lỗi
                    time.sleep(0.01)
            except Exception as e:
                logger.error(f"Cam {self.index}: Lỗi ngoại lệ: {e}")
                self.consecutive_failures += 1
                time.sleep(0.01)
            
            # Sleep tiêu chuẩn để giữ FPS ổn định (~60fps)
            time.sleep(0.015)

        if self.cap:
            self.cap.release()
        logger.info(f"CAMERA {self.index}: Thread kết thúc.")

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait()

    def is_active(self):
        return self._is_running and self.cap is not None and self.cap.isOpened()

def find_available_cameras(max_cameras_to_check=5) -> list[int]:
    available_cameras = []
    api_preference = _get_os_backend()
    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras