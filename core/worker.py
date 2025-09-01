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

logger = logging.getLogger(__name__)

class ProcessingWorker(QObject):
    finished = Signal(dict)

    def __init__(self):
        super().__init__()
        self.detector = ObjectDetector(model_path="my_model.pt")
        self.assets = self._load_assets()
        
        # --- THAY ĐỔI: Ánh xạ chính xác 3 object class của bạn ---
        # Key: Tên class mà model nhận diện được.
        # Value: (Hàm xử lý tương ứng, Tên tài sản (asset) để sử dụng).
        self.hit_handlers = {
            'bia_so_4': (handle_hit_bia_so_4, 'bia_so_4'),
            'bia_so_7_8': (handle_hit_bia_so_7, 'bia_so_7'), # Khi phát hiện 'bia_so_7_8' -> dùng handler và asset của bia 7
            'bia_so_8': (handle_hit_bia_so_8, 'bia_so_8'),
        }
        # ----------------------------------------------------------

        logger.info("Worker: Đã khởi tạo, tải xong mô hình và tài sản.")
        # --- THÊM VÀO: LOGIC "LÀM NÓNG" MODEL ---
        logger.info("Worker: Thực hiện warm-up cho mô hình YOLO...")
        try:
            # Tạo một ảnh giả (đen) với kích thước tiêu chuẩn
            dummy_image = np.zeros((480, 640, 3), dtype=np.uint8)
            # Chạy nhận diện một lần để buộc model khởi tạo hoàn toàn
            self.detector.detect(dummy_image)
            logger.info("Worker: Warm-up hoàn tất.")
        except Exception as e:
            logger.error(f"Worker: Lỗi trong quá trình warm-up: {e}")
        # ------------------------------------------

        logger.info("Worker: Đã khởi tạo, tải xong mô hình và tài sản.")

    def _load_assets(self):
        base_dir = "images"
        assets = {}
        target_names = ['bia_so_4', 'bia_so_7', 'bia_so_8']
        
        for name in target_names:
            img_path = os.path.join(base_dir, "original", f"{name}.png")
            img_alt_path = os.path.join(base_dir, "original", f"{name}_1.png")
            mask_path = os.path.join(base_dir, "mask", f"mask_{name}.png")
            
            img = cv2.imread(img_path)
            mask = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)

            if img is not None and mask is not None:
                # THAY ĐỔI: Sử dụng key đã được chuẩn hóa
                assets[name] = {
                    'original_img': img,
                    'original_img_alt': cv2.imread(img_alt_path),
                    'mask': mask
                }
            else:
                logger.error(f"LỖI: Không tìm thấy file tài sản cho '{name}'")
        return assets

    @Slot(np.ndarray, object)
    def process_image(self, photo_frame, calibrated_center):
        detections = self.detector.detect(image=photo_frame, conf=0.1)
        status, hit_info = check_object_center(detections, photo_frame, calibrated_center)

        result_data = None
        if status == "TRÚNG":
            detected_name = hit_info.get('name')
            
            # --- THAY ĐỔI: Dùng tra cứu trực tiếp thay vì vòng lặp ---
            # Logic này nhanh và chính xác hơn.
            handler_info = self.hit_handlers.get(detected_name)
            # ------------------------------------------------------

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
        else:
            result_data = handle_miss(hit_info, photo_frame)

        # Đóng gói lại kết quả cuối cùng
        final_package = {
            'time_str': datetime.now().strftime('%H:%M:%S'),
            'target_name': result_data.get('target'),
            'score': result_data.get('score'),
            'result_frame': result_data.get('image')
        }
        
        self.finished.emit(final_package)
        logger.info(f"Worker: Đã xử lý xong. Kết quả: {final_package['target_name']} - {final_package['score']} điểm.")