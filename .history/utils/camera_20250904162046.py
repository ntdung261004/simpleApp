# core/camera.py
import cv2
import logging
import sys

logger = logging.getLogger(__name__)

def _get_os_backend():
    """
    Hàm trợ giúp: Chọn API backend phù hợp với hệ điều hành để tăng độ ổn định.
    Sẽ được sử dụng bởi cả lớp Camera và hàm tìm kiếm để đảm bảo tính nhất quán.
    """
    if sys.platform == "win32":
        logger.debug("Sử dụng backend DSHOW cho Windows.")
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        logger.debug("Sử dụng backend AVFoundation cho macOS.")
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY  # Linux hoặc khác

class Camera:
    """
    Lớp quản lý việc tương tác với một thiết bị camera vật lý.
    """
    def __init__(self, index: int):
        self.index = index
        api_preference = _get_os_backend()
        
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"Không thể mở camera có chỉ số {self.index} với backend được chỉ định.")
        else:
            logger.info(f"Đã mở thành công camera có chỉ số {self.index}.")
            
            # === SỬA LỖI QUAN TRỌNG ===
            # Vô hiệu hóa việc đặt độ phân giải cứng.
            # Hãy để camera chạy ở độ phân giải mặc định của nó trước.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            # self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def isOpened(self) -> bool:
        """Kiểm tra xem camera có đang được mở và hoạt động hay không."""
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        """Lấy một khung hình (frame) từ camera."""
        if not self.isOpened():
            return False, None
            
        ret, frame = self.cap.read()
        if not ret:
            # Ghi log nếu không đọc được frame để dễ gỡ lỗi
            logger.warning(f"Không thể đọc khung hình từ camera index {self.index}.")
            return False, None
        
        return ret, frame
    
    def release(self):
        """Giải phóng thiết bị camera."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()
            logger.info(f"Đã giải phóng camera có chỉ số {self.index}")
            
def find_available_cameras(max_cameras_to_check=5):
    """Tìm các chỉ số (index) của camera đang có sẵn một cách đáng tin cậy."""
    logger.info("Bắt đầu tìm kiếm các camera khả dụng...")
    available_cameras = []
    
    # === SỬA LỖI QUAN TRỌNG ===
    # Sử dụng cùng một backend API như lớp Camera để đảm bảo nhất quán.
    api_preference = _get_os_backend()

    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
            
    logger.info(f"Các camera khả dụng được tìm thấy: {available_cameras}")
    return available_cameras