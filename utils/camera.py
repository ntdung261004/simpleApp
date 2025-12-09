# file: utils/camera.py
import cv2
import logging
import sys
import time
import numpy as np
from PySide6.QtCore import QThread, Signal

# Không dùng logger global trong run() để tránh xung đột
logger = logging.getLogger(__name__)

def _get_os_backend():
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

class CameraThread(QThread):
    frame_received = Signal(object) # Gửi ảnh đã resize (nhẹ hơn nhiều)
    error_occurred = Signal(int)
    log_signal = Signal(str, str)   # Gửi log về Main Thread

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._is_running = True
        self.cap = None
        self.last_frame_time = 0.0
        self.WATCHDOG_TIMEOUT = 3.0 # Timeout an toàn
        
        # Cấu hình kích thước đích (để resize ngay trong luồng)
        self.target_size = (480, 640) # (Width, Height)

    def run(self):
        # Hàm log an toàn tránh lỗi reentrant
        def log_safe(level, msg):
            self.log_signal.emit(level, msg)

        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        # Cố gắng set độ phân giải đầu vào
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            log_safe("ERROR", f"CAMERA {self.index}: Không thể mở thiết bị.")
            self.error_occurred.emit(self.index)
            return
        
        log_safe("INFO", f"CAMERA {self.index}: Bắt đầu stream (30 FPS).")
        self.last_frame_time = time.time()

        while self._is_running:
            # Watchdog: Kiểm tra treo camera
            if time.time() - self.last_frame_time > self.WATCHDOG_TIMEOUT:
                log_safe("ERROR", f"Cam {self.index}: WATCHDOG TIMEOUT.")
                self.error_occurred.emit(self.index)
                break

            try:
                ret, frame = self.cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    self.last_frame_time = time.time()
                    
                    # --- [TỐI ƯU] XỬ LÝ ẢNH NGAY TẠI ĐÂY ---
                    # 1. Crop về tỷ lệ 3:4
                    h, w = frame.shape[:2]
                    target_aspect = 3.0 / 4.0
                    new_w = int(h * target_aspect)
                    
                    if w > new_w:
                        start_x = (w - new_w) // 2
                        frame_cropped = frame[:, start_x : start_x + new_w]
                    else:
                        frame_cropped = frame
                        
                    # 2. Resize về kích thước đích (480x640)
                    frame_resized = cv2.resize(frame_cropped, self.target_size, interpolation=cv2.INTER_LINEAR)
                    
                    # 3. Gửi ảnh nhẹ về UI
                    self.frame_received.emit(frame_resized)
                else:
                    time.sleep(0.05)
                    
            except Exception as e:
                # Chỉ log 1 lần mỗi 2s để tránh spam lag máy
                if time.time() % 2 < 0.1: 
                    log_safe("ERROR", f"Cam {self.index}: Lỗi đọc frame: {e}")
                time.sleep(0.05)
            
            # [TỐI ƯU] Giới hạn ~30 FPS
            time.sleep(0.03)

        if self.cap:
            self.cap.release()
        log_safe("INFO", f"CAMERA {self.index}: Thread kết thúc.")

    def stop(self):
        """Dừng luồng an toàn. KHÔNG DÙNG TERMINATE TRÊN WINDOWS."""
        self._is_running = False
        self.quit()
        # Chờ luồng tự kết thúc việc đọc frame và release camera.
        self.wait() 

    def is_active(self):
        return self._is_running and self.cap is not None and self.cap.isOpened()

# --- [KHÔI PHỤC] HÀM QUAN TRỌNG BỊ THIẾU ---
def find_available_cameras(max_cameras_to_check=5) -> list[int]:
    """Quét nhanh các camera khả dụng."""
    available_cameras = []
    api_preference = _get_os_backend()
    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras