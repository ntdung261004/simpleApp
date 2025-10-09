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
        logger.info(f"Worker initialized with confidence threshold: {self.confidence_threshold}")
        
        self.hit_handlers = {
            'bia_4b': (handle_hit_bia_4b, 'bia_4b'),
            'bia_4c': (handle_hit_bia_4c, 'bia_4c')
        }
        self._warm_up_model()

    def _warm_up_model(self):
        logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy_image)
            logger.info("Worker: Warm-up hoàn tất.")
        except Exception as e:
            logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")
    
    def _load_assets(self):
        # (Hàm này giữ nguyên như trong file của bạn)
        assets = {}
        target_names = ['bia_4b', 'bia_4c']
        for name in target_names:
            img_path = resource_path(os.path.join("assets", "images", "original", f"{name}.png"))
            img_alt_path = resource_path(os.path.join("assets", "images", "warp", f"warp_{name}.png"))
            mask_path = resource_path(os.path.join("assets", "images", "mask", f"mask_{name}.png"))
            
            img = cv2.imread(img_path)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            if img is not None and mask is not None:
                assets[name] = { 'original_img': img, 'mask': mask, 'original_img_alt': None }
                if os.path.exists(img_alt_path):
                    img_alt = cv2.imread(img_alt_path)
                    if img_alt is not None:
                        assets[name]['original_img_alt'] = img_alt
            else:
                logger.error(f"LỖI: Không tìm thấy file tài sản chính cho '{name}'.")
        return assets

    # === THAY THẾ TOÀN BỘ HÀM NÀY ===
    @Slot(np.ndarray, str, str, object)
    def process_image(self, photo_frame, image_path, mode='practice', context=None):
        logger.info(f"Worker bắt đầu xử lý ảnh cho chế độ: '{mode}'")
        if photo_frame is None: return
            
        calibrated_center = context.get('calibrated_center') if mode == 'competition' else context

        # 1. Nhận dạng và kiểm tra trúng/trượt (Giữ nguyên)
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)
        status, hit_info = check_object_center(detections, photo_frame, calibrated_center)

        # 2. Xử lý logic để có ảnh kết quả (Giữ nguyên)
        result_data = None
        target_detected_raw = None
        if status == "TRÚNG":
            detected_name = hit_info.get('name')
            target_detected_raw = detected_name
            handler_info = self.hit_handlers.get(detected_name)
            if handler_info:
                handler_func, asset_key = handler_info
                asset_bundle = self.assets.get(asset_key)
                if asset_bundle:
                    result_data = handler_func(hit_info=hit_info, original_frame=photo_frame, **asset_bundle)
                else:
                    result_data = handle_miss(hit_info, photo_frame)
            else:
                result_data = handle_miss(hit_info, photo_frame)
        else:
            result_data = handle_miss(hit_info, photo_frame)
            target_detected_raw = "Trượt"
            
        # 3. LƯU ẢNH KẾT QUẢ (CHO THỐNG KÊ)
        final_image_to_save = result_data.get('image')
        if final_image_to_save is not None and image_path:
            try:
                os.makedirs(os.path.dirname(image_path), exist_ok=True)
                cv2.imwrite(image_path, final_image_to_save)
                logger.info(f"Worker: Đã lưu ảnh KẾT QUẢ (thống kê) tại {image_path}")
            except Exception as e:
                logger.error(f"Worker: Lỗi khi lưu ảnh kết quả: {e}")

        # 4. Đóng gói và gửi tín hiệu (Giữ nguyên)
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target'),
            'score': result_data.get('score'),
            'result_frame': result_data.get('image'),
            'coords': result_data.get('coords'),
            'image_path': image_path,
            'target_detected_raw': target_detected_raw
        }
        
        if mode == 'competition':
            self.competition_finished.emit(final_package, context)
        else:
            self.practice_finished.emit(final_package)
            
        logger.info(f"Worker: Đã xử lý xong. Chế độ: {mode}. Điểm: {final_package.get('score')}")