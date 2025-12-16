# file: utils/camera.py
import cv2
import logging
import sys
import time
import numpy as np
from PySide6.QtCore import QThread, Signal

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
    log_signal = Signal(str, str)

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._is_running = True
        self.cap = None
        self.last_frame_time = 0.0
        self.WATCHDOG_TIMEOUT = 3.0
        self.target_size = (480, 640)

    def run(self):
        def log_safe(level, msg):
            self.log_signal.emit(level, msg)

        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            log_safe("ERROR", f"CAMERA {self.index}: Không thể mở thiết bị.")
            self.error_occurred.emit(self.index)
            return
        
        log_safe("INFO", f"CAMERA {self.index}: Bắt đầu stream (30 FPS).")
        self.last_frame_time = time.time()

        while self._is_running:
            if time.time() - self.last_frame_time > self.WATCHDOG_TIMEOUT:
                log_safe("ERROR", f"Cam {self.index}: WATCHDOG TIMEOUT.")
                self.error_occurred.emit(self.index)
                break

            try:
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    self.last_frame_time = time.time()
                    
                    h, w = frame.shape[:2]
                    target_aspect = 3.0 / 4.0
                    new_w = int(h * target_aspect)
                    
                    if w > new_w:
                        start_x = (w - new_w) // 2
                        frame_cropped = frame[:, start_x : start_x + new_w]
                    else:
                        frame_cropped = frame
                        
                    frame_resized = cv2.resize(frame_cropped, self.target_size, interpolation=cv2.INTER_LINEAR)
                    self.frame_received.emit(frame_resized)
                else:
                    time.sleep(0.05)
            except Exception as e:
                time.sleep(0.05)
            
            time.sleep(0.03)

        if self.cap:
            self.cap.release()
        log_safe("INFO", f"CAMERA {self.index}: Thread kết thúc.")

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait() 

    def is_active(self):
        return self._is_running and self.cap and self.cap.isOpened()

def find_available_cameras(max_cameras_to_check=5) -> list[int]:
    """Quét camera khả dụng (An toàn)."""
    available_cameras = []
    api_preference = _get_os_backend()
    for i in range(max_cameras_to_check):
        try:
            # [FIX] Thử mở và đóng nhanh để kiểm tra
            cap = cv2.VideoCapture(i, api_preference)
            if cap.isOpened():
                available_cameras.append(i)
                cap.release()
            # [FIX] Thêm delay cực nhỏ để Driver kịp nhả tài nguyên
            time.sleep(0.05) 
        except:
            pass
    return available_cameras