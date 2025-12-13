# file: core/saver.py
import cv2
import logging
import queue
import numpy as np  # [FIX] Thêm thư viện numpy
from PySide6.QtCore import QThread

logger = logging.getLogger(__name__)

class ImageSaver(QThread):
    def __init__(self):
        super().__init__()
        self.queue = queue.Queue()
        self._is_running = True

    def save_image(self, image, path):
        """Thêm ảnh vào hàng đợi để lưu."""
        if image is None or not path:
            return
        self.queue.put((image, path))

    def run(self):
        """Vòng lặp xử lý hàng đợi."""
        logger.info("ImageSaver: Thread bắt đầu chạy.")
        while self._is_running:
            try:
                # Chờ lấy ảnh từ queue với timeout 1s để kiểm tra cờ _is_running
                image, path = self.queue.get(timeout=1)
                try:
                    # [FIX] Thay thế cv2.imwrite để hỗ trợ đường dẫn tiếng Việt (Unicode)
                    # Encode ảnh sang định dạng mong muốn (ví dụ .png) trong bộ nhớ
                    is_success, im_buf_arr = cv2.imencode(".png", image)
                    
                    if is_success:
                        # Ghi dữ liệu binary xuống đĩa bằng phương thức của numpy
                        # Cách này bypass được lỗi Unicode của OpenCV trên Windows
                        im_buf_arr.tofile(path)
                        logger.info(f"ImageSaver: Đã lưu {path}")
                    else:
                        logger.error(f"ImageSaver: Thất bại khi encode ảnh {path}")

                except Exception as e:
                    logger.error(f"ImageSaver: Lỗi ngoại lệ khi lưu {path}: {e}")
                finally:
                    self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"ImageSaver: Lỗi luồng: {e}")

    def stop(self):
        """Dừng luồng an toàn."""
        self._is_running = False
        self.wait()
        logger.info("ImageSaver: Thread đã dừng.")