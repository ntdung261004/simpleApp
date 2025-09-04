# file: utils/camera.py
import cv2
import logging
import sys

logger = logging.getLogger(__name__)

def _get_os_backend():

    if sys.platform == "darwin":  # macOS
        return cv2.CAP_AVFOUNDATION
    if sys.platform == "win32":  # Windows
        return cv2.CAP_DSHOW
    return cv2.CAP_ANY  # Linux hoặc khác

def find_available_cameras(max_cameras_to_check=5):
    """
    Tìm các chỉ số (index) của camera đang có sẵn một cách đáng tin cậy.
    """
    available_indices = []
    backend = _get_os_backend()
    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, backend)
        if cap and cap.isOpened():
            available_indices.append(i)
            cap.release()
    logger.info(f"Các camera khả dụng được tìm thấy: {available_indices}")
    return available_indices

class Camera:
    """
    Lớp quản lý việc kết nối và đọc dữ liệu từ một camera cụ thể.
    """
    def __init__(self, index: int):
        self.index = index
        self.cap = cv2.VideoCapture(index, _get_os_backend())

        if self.cap.isOpened():
            ##self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            logger.info(f"Đã mở thành công camera tại chỉ số {index}")
        else:
            logger.error(f"Không thể mở camera tại chỉ số {index}")
            self.cap = None

    def isOpened(self):
        """Kiểm tra camera có đang mở không."""
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        """Đọc một khung hình từ camera, tương thích với self.cam.read()."""
        if not self.isOpened():
            return False, None
        return self.cap.read()

    def release(self):
        """Giải phóng camera."""
        if self.isOpened():
            self.cap.release()
            logger.info(f"Đã giải phóng camera tại chỉ số {self.index}")