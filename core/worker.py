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
logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    finished = Signal(dict)

    # --- BẮT ĐẦU THAY ĐỔI ---
    def __init__(self, config: dict): # << Nhận 'config' từ main.py
        super().__init__()
        model_path = resource_path("assets/models/my_modelv8m.pt")
        self.detector = ObjectDetector(model_path=model_path)
        self.assets = self._load_assets()

        # Lấy ngưỡng tin cậy từ config, nếu không có thì dùng 0.75
        self.confidence_threshold = config.get('yolo_confidence_threshold', 0.75)
        logger.info(f"Worker initialized with confidence threshold: {self.confidence_threshold}")
    # --- KẾT THÚC THAY ĐỔI ---
        
        self.hit_handlers = {
            'bia_so_4': (handle_hit_bia_so_4, 'bia_so_4'),
            'bia_so_7_8': (handle_hit_bia_so_7, 'bia_so_7'),
            'bia_so_8': (handle_hit_bia_so_8, 'bia_so_8'),
        }

        # Logic "làm nóng" model
        logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy_image)
            logger.info("Worker: Warm-up hoàn tất.")
        except Exception as e:
            logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")

    def _load_assets(self):
        # Hàm này giữ nguyên như trong file của bạn
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
        # --- BẮT ĐẦU THAY ĐỔI ---
        # Sử dụng ngưỡng tin cậy đã đọc từ config
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)
        # --- KẾT THÚC THAY ĐỔI ---

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

        if result_data.get('score') is not None and result_data.get('score') > 0:
            final_image_to_save = result_data.get('image')
            if final_image_to_save is not None:
                try:
                    cv2.imwrite(image_path, final_image_to_save)
                    logger.info(f"Worker: Đã ghi đè ảnh kết quả tại {image_path}")
                except Exception as e:
                    logger.error(f"Worker: Lỗi khi ghi đè ảnh kết quả: {e}")

        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target'),
            'score': result_data.get('score'),
            'result_frame': result_data.get('image'),
            'coords': result_data.get('coords'),
            'image_path': image_path,
            'target_detected_raw': target_detected_raw
        }
        
        self.finished.emit(final_package)
        logger.info(f"Worker: Đã xử lý xong. Kết quả: {final_package['target_name']} - {final_package['score']} điểm.")