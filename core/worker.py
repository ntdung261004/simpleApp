# core/worker.py
import logging
import cv2
import numpy as np
import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot

from module.detection_module import ObjectDetector
from utils.processing import check_object_center
from utils.handles import handle_hit_bia_so_4, handle_hit_bia_so_7, handle_hit_bia_so_8, handle_miss
from utils.resource_path import resource_path
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    finished = Signal(dict)

    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.detector = None
        
        self._initialize_detector()

        self.assets = self._load_assets()
        self.confidence_threshold = self.config.get('yolo_confidence_threshold', 0.75)
        logger.info(f"Worker initialized with confidence threshold: {self.confidence_threshold}")
        
        self.hit_handlers = {
            'bia_so_4': (handle_hit_bia_so_4, 'bia_so_4'),
            'bia_so_7_8': (handle_hit_bia_so_7, 'bia_so_7'),
            'bia_so_8': (handle_hit_bia_so_8, 'bia_so_8'),
        }

        if self.detector:
            logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
            try:
                dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
                self.detector.detect(dummy_image)
                logger.info("Worker: Warm-up hoàn tất.")
            except Exception as e:
                logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")

    def _initialize_detector(self):
        model_filename = self.config.get("yolo_model_name")
        if not model_filename:
            logger.critical("Config không chứa 'yolo_model_name'. Không thể khởi tạo AI.")
            return

        model_path = os.path.join(APP_DATA_DIR, model_filename)

        if not os.path.exists(model_path):
            logger.critical(f"Không tìm thấy file model tại đường dẫn '{model_path}'. Worker không thể hoạt động.")
            return

        logger.info(f"Đang khởi tạo detector với model tại: {model_path}")
        self.detector = ObjectDetector(model_path=model_path)
        
    def _load_assets(self):
        assets = {}
        target_names = ['bia_so_4', 'bia_so_7', 'bia_so_8']
        
        for name in target_names:
            img_path = resource_path(os.path.join("assets", "images", "original", f"{name}.png"))
            img_alt_path = resource_path(os.path.join("assets", "images", "original", f"{name}_1.png"))
            mask_path = resource_path(os.path.join("assets", "images", "mask", f"mask_{name}.png"))
            
            img = cv2.imread(img_path)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            if img is not None and mask is not None:
                assets[name] = {
                    'original_img': img,
                    'original_img_alt': cv2.imread(img_alt_path),
                    'mask': mask
                }
            else:
                logger.error(f"LỖI: Không tìm thấy file tài sản cho '{name}' tại đường dẫn dự kiến.")
        return assets

    @Slot(np.ndarray, object, str)
    def process_image(self, photo_frame, calibrated_center, image_path):
        if not self.detector or not self.detector.model:
            logger.error("Detector chưa được khởi tạo. Hủy bỏ xử lý ảnh.")
            error_package = {
                'time_str': datetime.now().strftime('%H:%M:%S'),
                'target_name': "Lỗi Model AI",
                'score': 0, 'result_frame': photo_frame, 'coords': None,
                'image_path': image_path, 'target_detected_raw': "ERROR"
            }
            self.finished.emit(error_package)
            return
            
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)

        status, hit_info = check_object_center(detections, photo_frame, calibrated_center)

        result_data = None
        target_detected_raw = None
        if status == "TRÚNG":
            detected_name = hit_info.get('name')
            target_detected_raw = detected_name
            handler_info = self.hit_handlers.get(detected_name)

            if handler_info:
                handler_func, asset_key = handler_info
                asset_bundle = self.assets[asset_key]
                result_data = handler_func(
                    hit_info=hit_info,
                    original_frame=photo_frame,
                    **asset_bundle
                )
            else:
                logger.warning(f"Bắn trúng '{detected_name}' nhưng không có handler được định nghĩa.")
                result_data = handle_miss(hit_info, photo_frame)
                target_detected_raw = "Trượt" 
        else:
            result_data = handle_miss(hit_info, photo_frame)
            target_detected_raw = "Trượt" 

        # --- [TỐI ƯU] LOẠI BỎ VIỆC GHI ĐĨA TẠI ĐÂY ---
        # Việc lưu ảnh sẽ được chuyển cho ImageSaver ở Controller xử lý bất đồng bộ.
        # Worker chỉ trả về ảnh kết quả (đã vẽ tâm) thông qua Signal.
        
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target'),
            'score': result_data.get('score'),
            'result_frame': result_data.get('image'), # Ảnh này sẽ được gửi đi lưu
            'coords': result_data.get('coords'),
            'image_path': image_path,
            'target_detected_raw': target_detected_raw
        }
        
        self.finished.emit(final_package)
        logger.info(f"Worker: Đã xử lý xong. Kết quả: {final_package['target_name']} - {final_package['score']} điểm.")