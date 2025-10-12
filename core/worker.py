# core/worker.py
import logging
import cv2
import numpy as np
import os
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot

from module.detection_module import ObjectDetector
from utils.processing import check_object_center
from utils.handles import handle_hit_bia_4b, handle_hit_bia_4c, handle_miss
from utils.resource_path import resource_path

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    practice_finished = Signal(dict)
    competition_finished = Signal(dict, object)

    def __init__(self, config: dict):
        super().__init__()
        model_path = resource_path("assets/models/K54v2.pt")
        self.detector = ObjectDetector(model_path=model_path)
        self.assets = self._load_assets()
        self.confidence_threshold = config.get('yolo_confidence_threshold', 0.45)
        self.hit_handlers = {
            'bia_4b': (handle_hit_bia_4b, 'bia_4b'),
            'bia_4c': (handle_hit_bia_4c, 'bia_4c')
        }
        self._warm_up_model()

    def _warm_up_model(self):
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy_image); logger.info("Worker: Warm-up model thành công.")
        except Exception as e: logger.error(f"Worker: Lỗi khi warm-up model: {e}")
            
    def _load_assets(self):
        try:
            assets = {
                'bia_4b': {'original_img': cv2.imread(resource_path("assets/images/original/bia_4b.png")), 'mask': cv2.imread(resource_path("assets/images/mask/mask_4b.png"), cv2.IMREAD_GRAYSCALE)},
                'bia_4c': {'original_img': cv2.imread(resource_path("assets/images/original/bia_4c.png")), 'mask': cv2.imread(resource_path("assets/images/mask/mask_4c.png"), cv2.IMREAD_GRAYSCALE)}
            }
            for key in assets:
                alt_path = resource_path(os.path.join("assets", "images", "warp", f"warp_{key}.png"))
                assets[key]['original_img_alt'] = cv2.imread(alt_path) if os.path.exists(alt_path) else None
            return assets
        except Exception as e:
            logger.error(f"Worker: Lỗi nghiêm trọng khi tải tài nguyên: {e}"); return None

    @Slot(np.ndarray, str, str, object)
    def process_image(self, photo_frame, image_path, mode, metadata):
        if self.assets is None or photo_frame is None: return

        aim_point = metadata.get('aim_point') if isinstance(metadata, dict) else None
        detections = self.detector.detect(photo_frame, conf=self.confidence_threshold)
        status, hit_info = check_object_center(detections, photo_frame, aim_point)

        result_data = {}; target_detected_raw = "N/A"
        
        if status == "TRÚNG":
            target_name = hit_info.get('name')
            target_detected_raw = target_name
            handler_info = self.hit_handlers.get(target_name)
            
            if handler_info:
                handler_func, asset_key = handler_info
                asset_bundle = self.assets.get(asset_key)
                if asset_bundle:
                    result_data = handler_func(hit_info=hit_info, original_frame=photo_frame, **asset_bundle)
            
            if not result_data or result_data.get('score', 0) == 0:
                 result_data = handle_miss(hit_info, photo_frame)
                 target_detected_raw = "Trượt" # Ghi đè lại nếu điểm là 0
        else: # status == "TRƯỢT"
            result_data = handle_miss(hit_info, photo_frame)
            target_detected_raw = "Trượt"
        
        # Lưu ảnh gốc (để train)
        if image_path:
            try: cv2.imwrite(image_path, photo_frame)
            except Exception as e: logger.error(f"Worker: Lỗi khi lưu ảnh gốc: {e}")

        # Đóng gói kết quả
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target', 'Trượt'),
            'score': result_data.get('score', 0),
            'result_frame': result_data.get('image'), # Ảnh này là BIA GIẤY (nếu trúng) hoặc CAM GỐC (nếu trượt)
            'coords': result_data.get('coords'),
            'image_path': image_path,
            'target_detected_raw': target_detected_raw,
            'aim_point_used': aim_point
        }
        
        if mode == 'practice':
            self.practice_finished.emit(final_package)
        elif mode == 'competition':
            self.competition_finished.emit(final_package, metadata)