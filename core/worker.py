# file: core/worker.py
import logging
import cv2
import numpy as np
import os
import time
from datetime import datetime
from PySide6.QtCore import QObject, Signal, Slot

from module.detection_module import ObjectDetector
from utils.processing import check_object_center
from utils.handles import handle_hit_bia_4b, handle_hit_bia_4c, handle_miss
from utils.resource_path import resource_path
from config import APP_DATA_DIR

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    practice_finished = Signal(dict)
    competition_finished = Signal(dict, object)

    def __init__(self, config: dict):
        super().__init__()
        self.is_initialized = False
        try:
            logger.info("Worker: Bắt đầu khởi tạo...")
            model_relative_path = config.get("yolo_model_path", "assets/models/K54v2.pt")
            model_path = os.path.join(APP_DATA_DIR, model_relative_path)
            logging.info(f"Worker: Đang tải model từ: {model_path}")

            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Không tìm thấy file model AI tại: {model_path}. Vui lòng kiểm tra lại file config.json và sự tồn tại của file.")

            self.detector = ObjectDetector(model_path=model_path)
            if self.detector.model is None:
                raise RuntimeError("Không thể tải model YOLO.")

            self.assets = self._load_assets()
            if self.assets is None:
                raise RuntimeError("Không thể tải các file tài nguyên ảnh.")

            self.confidence_threshold = config.get('yolo_confidence_threshold', 0.45)
            self.hit_handlers = {
                'bia_4b': (handle_hit_bia_4b, 'bia_4b'),
                'bia_4c': (handle_hit_bia_4c, 'bia_4c')
            }
            
            self._warm_up_model()
            self.is_initialized = True
            logger.info("Worker: Khởi tạo thành công.")
        except Exception as e:
            logger.critical(f"Worker: KHỞI TẠO THẤT BẠI. Lỗi: {e}", exc_info=True)
            self.is_initialized = False

    def _warm_up_model(self):
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy_image)
            logger.info("Worker: Warm-up model thành công.")
        except Exception as e:
            logger.error(f"Worker: Lỗi khi warm-up model: {e}")
            
    def _load_assets(self):
        try:
            assets = {
                'bia_4b': {'original_img': cv2.imread(resource_path("assets/images/original/bia_4b.png")), 'mask': cv2.imread(resource_path("assets/images/mask/mask_4b.png"), cv2.IMREAD_GRAYSCALE)},
                'bia_4c': {'original_img': cv2.imread(resource_path("assets/images/original/bia_4c.png")), 'mask': cv2.imread(resource_path("assets/images/mask/mask_4c.png"), cv2.IMREAD_GRAYSCALE)}
            }
            for key, value in assets.items():
                if value['original_img'] is None or value['mask'] is None:
                    logger.error(f"Lỗi tải tài nguyên cho '{key}'.")
                    return None
                alt_path = resource_path(os.path.join("assets", "images", "warp", f"warp_{key}.png"))
                value['original_img_alt'] = cv2.imread(alt_path) if os.path.exists(alt_path) else None
            return assets
        except Exception as e:
            logger.error(f"Worker: Lỗi nghiêm trọng khi tải tài nguyên: {e}", exc_info=True)
            return None

    @Slot(np.ndarray, str, str, object)
    def process_image(self, photo_frame, image_path, mode, metadata):
        """Slot này sẽ thực hiện toàn bộ công việc xử lý ảnh."""
        if not self.is_initialized or photo_frame is None:
            logger.warning("Worker chưa sẵn sàng hoặc không có ảnh, bỏ qua xử lý.")
            return

        logger.info(f"Worker: Đã nhận ảnh cho chế độ '{mode}'. Bắt đầu xử lý...")
        
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
            
            if not result_data or result_data.get('score', 0) == 0 and target_detected_raw != "Trượt":
                 result_data = handle_miss(hit_info, photo_frame)
                 target_detected_raw = "Trượt"
        else:
            result_data = handle_miss(hit_info, photo_frame)
            target_detected_raw = "Trượt"
        
        if image_path:
            frame_to_save = result_data.get('image', photo_frame)
            try: cv2.imwrite(image_path, frame_to_save)
            except Exception as e: logger.error(f"Worker: Lỗi khi lưu ảnh: {e}")

        safe_coords = None
        raw_coords = result_data.get('coords')
        if raw_coords is not None and isinstance(raw_coords, (tuple, list)) and len(raw_coords) == 2:
            try:
                safe_coords = (int(raw_coords[0]), int(raw_coords[1]))
            except (ValueError, TypeError):
                logger.warning(f"Không thể chuyển đổi tọa độ {raw_coords} sang kiểu int.")
                safe_coords = None
        
        if mode == 'practice':
            practice_package = {
                'time_str': datetime.now().strftime('%H%M:%S'),
                'target_name': result_data.get('target', 'Trượt'),
                'score': result_data.get('score', 0),
                'result_frame': result_data.get('image'),
                'coords': safe_coords,
                'image_path': image_path,
                'target_detected_raw': target_detected_raw,
            }
            logger.info(f"LOG WORKER (PRACTICE): Chuẩn bị gửi đi - Coords: {practice_package.get('coords')}")
            self.practice_finished.emit(practice_package)
            
        elif mode == 'competition':
            competition_package = {
                'score': result_data.get('score', 0),
                'coords': safe_coords,
                'image_path': image_path,
                'target_detected_raw': target_detected_raw
            }
            # === BẮT ĐẦU VÙNG THÊM MỚI: GHI LOG CHI TIẾT ===
            logger.info(f"LOG WORKER (COMPETITION): Chuẩn bị gửi đi - Gói dữ liệu: {competition_package}")
            # === KẾT THÚC VÙNG THÊM MỚI ===
            self.competition_finished.emit(competition_package, metadata)