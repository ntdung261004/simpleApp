# core/camera.py
import cv2
import logging
import sys

logger = logging.getLogger(__name__)

class Camera:
    """
    Lớp quản lý việc tương tác với một thiết bị camera vật lý.
    """
    def __init__(self, index: int):
        """
        Khởi tạo một đối tượng camera.
        
        Args:
            index (int): Chỉ số của thiết bị camera (ví dụ: 0, 1, 2).
        """
        self.index = index
        
        # Sử dụng API backend phù hợp với hệ điều hành để tăng độ ổn định
        api_preference = cv2.CAP_ANY # Mặc định
        if sys.platform == "darwin": # Nếu là macOS
            api_preference = cv2.CAP_AVFOUNDATION
            logger.info("Sử dụng backend AVFoundation cho macOS.")
        elif sys.platform == "win32": # Nếu là Windows
            api_preference = cv2.CAP_DSHOW
            logger.info("Sử dụng backend DSHOW cho Windows.")
        
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"Không thể mở camera có chỉ số {self.index}")
        else:
            logger.info(f"Đã mở thành công camera có chỉ số {self.index}")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def get_index(self) -> int:
        """
        Trả về chỉ số của camera mà đối tượng này đang quản lý.
        """
        return self.index

    def ispened(self) -> bool:
        """
        Kiểm tra xem camera có đang được mở và hoạt động hay không.
        """
        return self.cap.isOpened()

    def grab(self):
        """
        Lấy một khung hình (frame) từ camera.
        
        Returns:
            numpy.ndarray: Khung hình đọc được, hoặc None nếu có lỗi.
        """
        if not self.is_opened():
            return None
            
        ret, frame = self.cap.read()
        if not ret:
            return None
        
        return frame
    
    def release(self):
        """
        Giải phóng thiết bị camera.
        """
        if self.is_opened() and self.cap is not None:
            self.cap.release()
            logger.info(f"Đã giải phóng camera có chỉ số {self.index}")
            
def find_available_cameras(max_cameras_to_check=10):
    available_cameras = []
    for i in range(max_cameras_to_check):
        api_preference = cv2.CAP_ANY
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    return available_cameras