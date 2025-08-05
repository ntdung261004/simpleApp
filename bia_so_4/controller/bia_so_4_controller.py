# bia_so_4_controller.py
from ultralytics import YOLO
import cv2
from typing import Dict, Optional, Tuple
from bia_so_4.service.bia_so_4_service import BiaSo4Service
import logging

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = "/Users/thaiduong/Desktop/python/webcam_capture_app_mac/runs/detect/train2/weights/best.pt"
TARGET_LABEL = "bia_so_4"

class BiaSo4Controller:
    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, service: Optional[BiaSo4Service] = None):
        logger.info("[controller] Khởi tạo controller")
        self.model = YOLO(model_path)
        self.service = service or BiaSo4Service()
        self.target_label = TARGET_LABEL

    def test_controller(self):
        logger.debug("[controller] Controller được gọi")

    def check_bia_hit(self, frame, target_label: Optional[str] = None, conf_thresh: float = 0.3) -> Dict:
        label_to_check = target_label or self.target_label
        h, w = frame.shape[:2]
        cx, cy = w / 2.0, h / 2.0

        res = {
            "detected": False,
            "center_in_box": False,
            "box": None,
            "confidence": 0.0,
        }

        try:
            results = self.model(frame, verbose=False)[0]
        except Exception:
            logger.exception("Lỗi khi chạy model inference")
            return res

        if not hasattr(results, "boxes") or results.boxes is None:
            return res

        for box, cls, conf in zip(
            results.boxes.xyxy.cpu().numpy(),
            results.boxes.cls.cpu().numpy(),
            results.boxes.conf.cpu().numpy(),
        ):
            label = self.model.names[int(cls)]
            if label == label_to_check and conf >= conf_thresh:
                res["detected"] = True
                res["box"] = box.tolist()
                res["confidence"] = float(conf)
                res["center_in_box"] = self.service.check_hit_logic((cx, cy), box)
                break
        return res

    def process_shot_result(self, frame, box) -> Tuple[Optional[any], Optional[float]]:
        """
        Xử lý toàn bộ logic tính điểm sau khi đã xác định hit.
        """
        warped_bia, position1 = self.service.extract_and_warp_to_standard(frame, box)
        if warped_bia is None:
            return None, "không cắt được ảnh bia!"

        original_path = "images/original/original_bia_so_4.jpg"
        img_Warp_To_Original, position2 = self.service.warp_back_to_original(original_path, position1)
        if img_Warp_To_Original is None:
            return None, "không warp về ảnh chuẩn được!"

        score = self.service.calculate_score(position2)

        # Thêm logic vẽ hình vào đây
        x, y = int(position2[0]), int(position2[1])
        cv2.circle(img_Warp_To_Original, (x, y), 6, (0, 0, 255), -1)
        cv2.putText(
            img_Warp_To_Original,
            f"{score}",
            (x + 20, y - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 0, 0),
            3,
        )

        return img_Warp_To_Original, score
