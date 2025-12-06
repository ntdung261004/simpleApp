# file: utils/camera.py
import cv2
import logging
import sys
import time
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

    def __init__(self, index: int):
        super().__init__()
        self.index = index
        self._is_running = True
        self.cap = None
        self.last_frame_time = 0.0
        # Nếu quá 2 giây không có frame -> Báo lỗi
        self.WATCHDOG_TIMEOUT = 2.0 

    def run(self):
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        # Cố gắng set độ phân giải
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            logger.error(f"CAMERA {self.index}: Không thể mở thiết bị.")
            self.error_occurred.emit(self.index)
            return
        
        logger.info(f"CAMERA {self.index}: Bắt đầu stream.")
        self.last_frame_time = time.time()

        while self._is_running:
            # 1. Cơ chế Watchdog: Kiểm tra thời gian trôi qua
            if time.time() - self.last_frame_time > self.WATCHDOG_TIMEOUT:
                logger.error(f"Cam {self.index}: WATCHDOG TIMEOUT (Mất kết nối quá lâu).")
                self.error_occurred.emit(self.index)
                break

            try:
                # Đọc frame (non-blocking nếu có thể, nhưng OpenCV thường block)
                ret, frame = self.cap.read()
                
                if ret and frame is not None and frame.size > 0:
                    self.last_frame_time = time.time() # Cập nhật thời gian sống
                    self.frame_received.emit(frame)
                else:
                    # Nếu read trả về False (mất kết nối tức thì)
                    time.sleep(0.05) # Nghỉ nhẹ để tránh spam CPU
                    
            except Exception as e:
                logger.error(f"Cam {self.index}: Lỗi ngoại lệ: {e}")
                time.sleep(0.05)
            
            # Giới hạn FPS khoảng ~60fps để mượt mà nhưng không ngốn CPU
            time.sleep(0.015)

        if self.cap:
            self.cap.release()
        logger.info(f"CAMERA {self.index}: Thread kết thúc.")

    def stop(self):
        self._is_running = False
        # Chờ luồng kết thúc an toàn
        self.quit()
        
        # --- FIX CRASH: Wait kỹ hơn và xử lý terminate đúng cách ---
        if not self.wait(2000): # Chờ tối đa 2s để luồng tự đóng
            logger.warning(f"Cam {self.index}: Không phản hồi, buộc dừng (terminate).")
            self.terminate() # Cưỡng chế tắt
            self.wait() # QUAN TRỌNG: Chờ cho đến khi terminate hoàn tất trước khi hủy object
        # -----------------------------------------------------------

    def is_active(self):
        return self._is_running and self.cap is not None and self.cap.isOpened()

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