# file: utils/camera.py
import cv2
import logging
import sys

logger = logging.getLogger(__name__)

def _get_os_backend():
    """Lấy backend camera phù hợp với hệ điều hành để tăng tốc độ quét."""
    if sys.platform == "win32":
        return cv2.CAP_DSHOW
    if sys.platform == "darwin":
        return cv2.CAP_AVFOUNDATION
    return cv2.CAP_ANY

class Camera:
    def __init__(self, index: int):
        self.index = index
        api_preference = _get_os_backend()
        self.cap = cv2.VideoCapture(self.index, api_preference)

        if not self.cap.isOpened():
            logger.error(f"CAMERA: Lỗi khi mở camera index {self.index}.")
        else:
            logger.info(f"CAMERA: Đã mở thành công camera index {self.index}.")
            # Cố gắng đặt độ phân giải mong muốn
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    def isOpened(self) -> bool:
        return self.cap is not None and self.cap.isOpened()

    def read(self):
        if not self.isOpened():
            return (False, None)
        ret, frame = self.cap.read()
        return (ret, frame)

    def release(self):
        if self.isOpened():
            self.cap.release()
            logger.info(f"CAMERA: Đã giải phóng camera index {self.index}.")

def find_available_cameras(max_cameras_to_check=5) -> list[int]:
    """
    Quét và trả về một danh sách các chỉ số (index) của các camera khả dụng.
    Đây là hàm được tối ưu để thay thế cho hàm đếm cũ.
    """
    logger.info("CAMERA: Bắt đầu quét các camera...")
    available_cameras = []
    api_preference = _get_os_backend()
    for i in range(max_cameras_to_check):
        cap = cv2.VideoCapture(i, api_preference)
        if cap.isOpened():
            available_cameras.append(i)
            cap.release()
    logger.info(f"CAMERA: Các camera tìm thấy: {available_cameras}")
    return available_cameras