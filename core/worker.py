# core/worker.py
import logging
import numpy as np
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot

from module.detection_module import ObjectDetector
from utils.processing import check_object_center

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    finished = Signal(dict)

    def __init__(self):
        super().__init__()
        self.detector = ObjectDetector(model_path="my_model.pt")
        logger.info("Worker: Đã khởi tạo và tải xong mô hình YOLO trong luồng nền.")

    @Slot(np.ndarray, object)
    def process_image(self, photo_frame, calibrated_center):
        logger.info("Worker: Nhận được yêu cầu xử lý ảnh...")
        
        detections = self.detector.detect(image=photo_frame, conf=0.5)
        status, hit_info = check_object_center(
            detections=detections,
            image=photo_frame,
            calibrated_center=calibrated_center
        )

        target_name = "Trượt"
        if status == "TRÚNG":
            target_name = hit_info.get('name', 'N/A')
        
        result_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': target_name,
            'score': "--",
            'result_frame': photo_frame
        }
        
        self.finished.emit(result_package)
        logger.info("Worker: Đã xử lý xong và gửi kết quả.")