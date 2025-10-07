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
    finished = Signal(dict)

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

        # Warm-up model
        logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
        try:
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            self.detector.detect(dummy_image)
            logger.info("Worker: Warm-up hoàn tất.")
        except Exception as e:
            logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")

    def _load_assets(self):
        assets = {}
        target_names = ['bia_4b', 'bia_4c']
        
        for name in target_names:
            # Đường dẫn tới ảnh gốc CHÍNH (chụp bằng điện thoại)
            img_path = resource_path(os.path.join("assets", "images", "original", f"{name}.png"))
            
            # --- BẮT ĐẦU NÂNG CẤP ---
            # Đường dẫn tới ảnh gốc PHỤ (chụp bằng webcam)
            img_alt_path = resource_path(os.path.join("assets", "images", "warp", f"warp_{name}.png"))
            # --- KẾT THÚC NÂNG CẤP ---

            mask_path = resource_path(os.path.join("assets", "images", "mask", f"mask_{name}.png"))
            
            img = cv2.imread(img_path)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            if img is not None and mask is not None:
                assets[name] = {
                    'original_img': img,
                    'mask': mask,
                    'original_img_alt': None # Khởi tạo là None
                }
                
                # --- BẮT ĐẦU NÂNG CẤP ---
                # Kiểm tra xem ảnh phụ có tồn tại không và tải nó
                if os.path.exists(img_alt_path):
                    img_alt = cv2.imread(img_alt_path)
                    if img_alt is not None:
                        assets[name]['original_img_alt'] = img_alt
                        logger.info(f"Đã tải thành công ảnh tham chiếu phụ cho '{name}'.")
                # --- KẾT THÚC NÂNG CẤP ---
            else:
                logger.error(f"LỖI: Không tìm thấy file tài sản chính cho '{name}'.")
        return assets

    @Slot(np.ndarray, object, str)
    def process_image(self, photo_frame, calibrated_center, image_path):
        """
        Hàm này chỉ nhận ảnh, xử lý và trả kết quả. 
        Nó không chịu trách nhiệm lưu ảnh training.
        """
        if photo_frame is None:
            logger.warning("Worker: Nhận được frame rỗng, bỏ qua xử lý.")
            return
            
        # 1. Phát hiện đối tượng trên ảnh được gửi đến
        detections = self.detector.detect(image=photo_frame, conf=self.confidence_threshold)

        # 2. Kiểm tra xem có trúng mục tiêu không
        status, hit_info = check_object_center(detections, photo_frame, calibrated_center)

        result_data = None
        target_detected_raw = None
        
        # 3. Xử lý logic trúng/trượt
        if status == "TRÚNG":
            detected_name = hit_info.get('name')
            target_detected_raw = detected_name
            handler_info = self.hit_handlers.get(detected_name)

            if handler_info:
                handler_func, asset_key = handler_info
                asset_bundle = self.assets.get(asset_key) # Dùng .get() để an toàn hơn
                if asset_bundle:
                    result_data = handler_func(
                        hit_info=hit_info,
                        original_frame=photo_frame,
                        **asset_bundle
                    )
                else:
                    logger.error(f"Không tìm thấy tài sản cho asset_key: {asset_key}")
                    result_data = handle_miss(hit_info, photo_frame)
            else:
                logger.warning(f"Bắn trúng '{detected_name}' nhưng không có handler được định nghĩa.")
                result_data = handle_miss(hit_info, photo_frame)
                target_detected_raw = "Trượt" 
        else:
            result_data = handle_miss(hit_info, photo_frame)
            target_detected_raw = "Trượt" 

        # =================== PHẦN QUAN TRỌNG NHẤT ===================
        #
        # ĐÃ XÓA BỎ HOÀN TOÀN KHỐI LOGIC GHI ĐÈ ẢNH (cv2.imwrite) TẠI ĐÂY.
        # Worker sẽ KHÔNG còn ghi đè lên file ảnh training sạch nữa.
        #
        # ==========================================================

        # 4. Đóng gói kết quả cuối cùng để gửi về giao diện
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target'),
            'score': result_data.get('score'),
            'result_frame': result_data.get('image'), # Ảnh KẾT QUẢ (có tâm đỏ) để hiển thị
            'coords': result_data.get('coords'),
            'image_path': image_path, # Vẫn gửi lại đường dẫn file gốc
            'target_detected_raw': target_detected_raw
        }
        
        self.finished.emit(final_package)
        logger.info(f"Worker: Đã xử lý xong. Kết quả: {final_package['target_name']} - {final_package['score']} điểm.")